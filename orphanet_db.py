import sqlite3
import xml.etree.ElementTree as ET
from functools import lru_cache


class orphanet_db:
    conn = sqlite3.connect("orphanet.db", check_same_thread=False)
    cursor = conn.cursor()

    def create_tables(self) -> None:
        # Create tables
        self.cursor.execute(
            """
            CREATE TABLE frequency
            (frequency_id INTEGER PRIMARY KEY, frequency_name TEXT)
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE disorders
            (disorder_id INTEGER PRIMARY KEY, orpha_code TEXT, disorder_name TEXT)
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE hpo_terms
            (hpo_id TEXT PRIMARY KEY, hpo_term TEXT)
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE disorder_associations (
                assoc_id INTEGER PRIMARY KEY,
                disorder_id INTEGER,
                hpo_id TEXT,
                frequency_id INTEGER,
                FOREIGN KEY(disorder_id) REFERENCES disorders(disorder_id),
                FOREIGN KEY(hpo_id) REFERENCES hpo_terms(hpo_id),
                FOREIGN KEY(frequency_id) REFERENCES frequency(frequency_id)
            )
            """
        )

        self.conn.commit()

    def insert_data(self) -> None:
        # Insert data into the frequency table
        frequency_names = [
            "Excluded (0%)",
            "Very rare (<4-1%)",
            "Occasional (29-5%)",
            "Frequent (79-30%)",
            "Very frequent (99-80%)",
            "Obligate (100%)",
        ]
        for i, name in enumerate(frequency_names):
            self.cursor.execute(
                "INSERT OR IGNORE INTO frequency VALUES (?, ?)", (i + 1, name)
            )

        xml_data = open("en_product4.xml", "r").read()

        root = ET.fromstring(xml_data)

        for disorder in root.findall(".//Disorder"):
            disorder_id = disorder.attrib.get("id")
            orpha_code = disorder.find("OrphaCode").text
            disorder_name = disorder.find("Name").text

            # Insert data into the disorders table
            self.cursor.execute(
                "INSERT OR IGNORE INTO disorders VALUES (?, ?, ?)",
                (disorder_id, orpha_code, disorder_name),
            )

            for association in disorder.findall(".//HPODisorderAssociation"):
                assoc_id = association.attrib.get("id")
                hpo_id = association.find("HPO/HPOId").text
                hpo_term = association.find("HPO/HPOTerm").text
                frequency_name = association.find("HPOFrequency/Name").text
                frequency_id = frequency_names.index(frequency_name) + 1

                # Insert data into the hpo_terms table
                self.cursor.execute(
                    "INSERT OR IGNORE INTO hpo_terms VALUES (?, ?)", (hpo_id, hpo_term)
                )

                # Insert data into the disorder_associations table
                self.cursor.execute(
                    "INSERT OR IGNORE INTO disorder_associations VALUES (?, ?, ?, ?)",
                    (assoc_id, disorder_id, hpo_id, frequency_id),
                )

        # Save (commit) the changes
        self.conn.commit()

    def create_orphanet_db(self) -> None:
        try:
            self.create_tables()
        except sqlite3.Error as e:
            print(" ".join(e.args))
            return

        self.insert_data()

    def get_disorders(self, hpo_ids: frozenset[str]) -> list:
        if (
            not hpo_ids
            or len(hpo_ids) == 0
            or (len(hpo_ids) == 1 and list(hpo_ids)[0] == "")
        ):
            return []

        # Get all disorders with the given hpo_ids
        insert = f"{','.join('?' * len(hpo_ids))}"

        query = f"""
            SELECT orpha_code, disorder_name, hpo_id, hpo_term, frequency_id
            FROM disorder_associations
            JOIN disorders USING (disorder_id)
            JOIN hpo_terms USING (hpo_id)
            JOIN frequency USING (frequency_id)
            WHERE hpo_id in ({insert}) AND frequency_id != 1
            ORDER BY disorder_id, hpo_id
        """
        self.cursor.execute(query, tuple(hpo_ids))

        return self.cursor.fetchall()


if __name__ == "__main__":
    o = orphanet_db()
    o.create_orphanet_db()
    disorders = o.get_disorders(
        frozenset(
            [
                "HP:0000716",  # Depression
                "HP:0000952",  # Jaundice
                "HP:0001369",  # Arthritis
                "HP:0002240",  # Hepatomegaly
                "HP:0012115",  # Hepatitis
            ]
        )
    )
    pass
