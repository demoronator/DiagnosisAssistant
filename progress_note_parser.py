import json
import torch
from transformers import (
    BertForSequenceClassification,
    BertTokenizerFast,
    Trainer,
    TrainingArguments,
)


class ProgressNoteParser:
    def __init__(
        self, hpo_file: str, model_checkpoint: str = "emilyalsentzer/Bio_ClinicalBERT"
    ):
        with open(hpo_file, "r") as file:
            self.hpo_terms = json.load(file)

        self.hpo_id_map = {term: i for i, term in enumerate(self.hpo_terms.keys())}

        self.sentences = [
            value["name"]
            + ". "
            + value["definition"]
            + ". "
            + ". ".join(value["synonyms"])
            + "."
            for value in self.hpo_terms.values()
        ]

        # Skip first entry because it is the root term
        self.sentences = self.sentences[1:]

        self.annotations = [self.hpo_id_map[term] for term in self.hpo_terms.keys()]
        # Skip first entry because it is the root term
        self.annotations = self.annotations[1:]

        self.tokenizer = BertTokenizerFast.from_pretrained(model_checkpoint)
        self.model = BertForSequenceClassification.from_pretrained(
            model_checkpoint, num_labels=len(self.hpo_id_map)
        )

    def train(self, epochs: int = 3, learning_rate: float = 5e-5):
        # Tokenize sentences to prepare them for the model
        train_encodings = self.tokenizer(
            self.sentences, truncation=True, padding=True, max_length=512
        )

        # Create a Dataset object to hold the encodings and labels
        train_dataset = HPOTermsDataset(train_encodings, self.annotations)

        # Define training arguments
        training_args = TrainingArguments(
            output_dir="./results",  # output directory
            num_train_epochs=epochs,  # total number of training epochs
            per_device_train_batch_size=8,  # batch size per device during training
            warmup_steps=500,  # number of warmup steps for learning rate scheduler
            weight_decay=0.01,  # strength of weight decay
            logging_dir="./logs",  # directory for storing logs
            learning_rate=learning_rate,
        )

        # Create a Trainer instance
        trainer = Trainer(
            model=self.model,  # the instantiated Transformers model to be trained
            args=training_args,  # training arguments, defined above
            train_dataset=train_dataset,  # training dataset
            tokenizer=self.tokenizer,
        )

        # Train the model
        trainer.train()

        # Save the trained model
        trainer.save_model("./model")

    def parse(self, text: str):
        # Load the trained model
        self.model = BertForSequenceClassification.from_pretrained("./model")

        # Preprocess the text
        inputs = self.tokenizer(
            text, truncation=True, padding=True, return_tensors="pt"
        )

        # Predict the HPO term
        outputs = self.model(**inputs)
        predicted_indices = torch.argmax(outputs.logits, dim=1)

        # Convert the predicted indices to HPO IDs
        predicted_hpo_ids = {
            v: k for k, v in self.hpo_id_map.items()
        }  # invert the dictionary
        return [predicted_hpo_ids[i.item()] for i in predicted_indices]


class HPOTermsDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item

    def __len__(self):
        return len(self.labels)


if __name__ == "__main__":
    pnp = ProgressNoteParser("hp.json")

    # Check if the trained model exists
    import os

    if os.path.exists("./model"):
        print("Loading the trained model...")
        pnp.model = BertForSequenceClassification.from_pretrained("./model")
    else:
        print("Training the model...")
        pnp.train(epochs=3, learning_rate=5e-5)

    print(
        pnp.parse(
            """
We present the case of a 14-year-old girl, admitted to our hospital for severe anemia and
ascites. Regarding her past medical records, she presented with partially investigated hepatic
cytolysis (serumaminotransferases repeatedly two to three times normal) during the last four years,
aswell as severe hemolytic anemia one year before,which required several blood transfusions.
However, no viral, autoimmune, ormetabolic disorderswere discovered to explain her symptoms.
Upon admission to our clinic, she presented with generalized itching, jaundice, and diffuse
edema that was palpable in the ankles and pretibial areas of her legs, as well as an enlarged
abdomen, indicating poor overall health. Duringmild palpation, she reportedmodest pain, and
her regular bowel habits in terms of color and consistency were noted. However, the abdomen's
diametermeasured around 70 cmdue to distention,making it difficult to determine the liver's
diameter, although the spleen was palpable 3-4 cm below the costalmargin. Additionally, low
puberty development was observed, with the patient having Tanner 1 on the Pubic hair score
and Tanner 2 on the Breast Development Scale, as per Tanner's score [11].
The initial investigation revealed severe anemia (hemoglobin = 3.3 g/dL) with low iron
and ferritin levels, without hemolytic elements (high level of conjugated
bilirubin = 1.37, low levels of iron level = 16.19 ㎍/dL and ferritin level = 7.75 ㎍/dL,
normal lactate dehydrogenase, negative Coombs tests), elevated aminotransferases (alanine
aminotransaminase—ALT = 98.6 U/L, aspartate aminotransferase—AST = 116.2 U/L), and
cholestatic syndrome.
        """
        )
    )
