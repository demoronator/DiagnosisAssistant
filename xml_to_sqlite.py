import sqlite3
import xml.etree.ElementTree as ET


def create_tables(cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    # Create tables
    cursor.execute(
        """
        CREATE TABLE disorders
        (disorder_id INTEGER PRIMARY KEY, orpha_code TEXT, disorder_name TEXT)
        """
    )

    cursor.execute(
        """
        CREATE TABLE hpo_terms
        (hpo_id TEXT PRIMARY KEY, hpo_term TEXT)
        """
    )

    cursor.execute(
        """
        CREATE TABLE disorder_associations
        (assoc_id INTEGER PRIMARY KEY, disorder_id INTEGER, hpo_id TEXT, frequency_name TEXT,
        FOREIGN KEY(disorder_id) REFERENCES disorders(disorder_id),
        FOREIGN KEY(hpo_id) REFERENCES hpo_terms(hpo_id))
        """
    )

    conn.commit()


def insert_data(cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    xml_data = open("en_product4.xml", "r").read()

    root = ET.fromstring(xml_data)

    for disorder in root.findall(".//Disorder"):
        disorder_id = disorder.attrib.get("id")
        orpha_code = disorder.find("OrphaCode").text
        disorder_name = disorder.find("Name").text

        # Insert data into the disorders table
        cursor.execute(
            "INSERT OR IGNORE INTO disorders VALUES (?, ?, ?)",
            (disorder_id, orpha_code, disorder_name),
        )

        for association in disorder.findall(".//HPODisorderAssociation"):
            assoc_id = association.attrib.get("id")

            hpo_id = association.find("HPO/HPOId").text
            hpo_term = association.find("HPO/HPOTerm").text

            frequency_name = association.find("HPOFrequency/Name").text

            # Insert data into the hpo_terms table
            cursor.execute(
                "INSERT OR IGNORE INTO hpo_terms VALUES (?, ?)", (hpo_id, hpo_term)
            )

            # Insert data into the disorder_associations table
            cursor.execute(
                "INSERT OR IGNORE INTO disorder_associations VALUES (?, ?, ?, ?)",
                (assoc_id, disorder_id, hpo_id, frequency_name),
            )

    # Save (commit) the changes
    conn.commit()


def xml_to_sqlite() -> None:
    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect("orphanet.db")
    cursor = conn.cursor()
    try:
        create_tables(cursor, conn)
    except sqlite3.OperationalError:
        print("Tables already exist")
        conn.close()
        return

    insert_data(cursor, conn)

    # Close the connection when done
    conn.close()


if __name__ == "__main__":
    xml_to_sqlite()
