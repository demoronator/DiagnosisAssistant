import pronto
from functools import lru_cache


# Constants
MIN_INPUT_LENGTH = 3
DEFAULT_ONTOLOGY_FILE = "hp.obo"


class HPO_explorer:
    preprocessed_terms: list

    def __init__(self, ontology_file) -> None:
        self.ont = pronto.ontology.Ontology(ontology_file)
        for term in self.ont.terms():
            full_desc = (
                str(term.name).lower()
                + " "
                + " ".join(syn.description.lower() for syn in term.synonyms)
                + " "
                + str(term.definition).lower()
            )
            self.preprocessed_terms.append((term.id, term.name, full_desc))

    @lru_cache(maxsize=1024)
    def find_terms(self, to_search: str, limit=None) -> list:
        # Strip the input of leading and trailing whitespace
        stripped = str.strip(to_search)
        if to_search != stripped:
            return self.find_terms(stripped, limit=limit)

        if not to_search or len(to_search) < MIN_INPUT_LENGTH:
            return []

        primary = []
        secondary = []
        words = to_search.lower().split()
        for term_id, term_name, full_desc in self.preprocessed_terms:
            if limit and limit <= len(primary):
                return (primary + secondary)[:limit]

            term = self.ont[term_id]
            if term.obsolete:
                continue

            # Check if all words in input are in the term name
            if all(word in term_name.lower() for word in words):
                primary.append((term_id, term_name))
            # Check synonyms
            elif 0 < len(term.synonyms) and all(word in full_desc for word in words):
                # The first synonym or definition with the most words in common with the input

                l = []
                for syn in term.synonyms:
                    l.append(syn.description)
                l.append(str(term.definition))

                syn = max(
                    l,
                    key=lambda s: 0
                    if s == term_name
                    else sum(word in s.lower() for word in words),
                )
                secondary.append((term_id, term_name, syn))

        return (primary + secondary)[:limit]

    @lru_cache(maxsize=1024)
    def get_superterms(self, term_id: str, distance: int | None = None) -> list:
        if not term_id or term_id not in self.ont:
            return []

        term: pronto.term.Term = self.ont[term_id]
        superterms = []
        results = term.superclasses(distance=distance, with_self=False)
        for superterm in results:
            superterms.append((superterm.id, superterm.name))

        return superterms

    def get_termname(self, term_id: str) -> str:
        if not term_id or term_id not in self.ont:
            return ""

        name = str(self.ont[term_id].name)
        return name


if __name__ == "__main__":
    hpo = HPO_explorer(DEFAULT_ONTOLOGY_FILE)

    # Test the function with an example term
    print(hpo.find_terms("Weight", limit=15), "\n")

    # Find the superterms of the term 'Childhood-onset truncal obesity'
    print(hpo.get_superterms("HP:0008915", distance=3))
