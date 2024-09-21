import re
import os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

import numpy as np
import pandas as pd
import re
from tqdm import tqdm  # For progress bar


def encode_kaski(word_df, bigram_occurrences):
    # Dimensions of the word_df (used to create feature_df)
    word_encoding_length, word_number_length = word_df.shape

    # Initialize the feature DataFrame (twice the rows of word_df)
    feature_df = pd.DataFrame(
        np.zeros((word_encoding_length * 2, word_number_length)),
        columns=word_df.columns,
    )

    print(f"Encoding words...")

    # Progress bar
    word_names = word_df.columns
    for cnames in tqdm(word_names, total=word_number_length):
        # Match bigrams that contain the word (cnames) as the first word
        match_all = [
            bool(re.search(rf"\b{cnames}\b", bigram, flags=re.IGNORECASE))
            for bigram in bigram_occurrences.columns
        ]
        all_match_bigrams = bigram_occurrences.loc[:, match_all]

        # Ensure all_match_bigrams is a DataFrame, even if it contains a single column
        if isinstance(all_match_bigrams, pd.Series):
            all_match_bigrams = all_match_bigrams.to_frame()

        # Match bigrams where 'cnames' is the first word
        match_names_first = [
            bool(re.match(rf"^{cnames} ", bigram, flags=re.IGNORECASE))
            for bigram in all_match_bigrams.columns
        ]
        word_set_first = all_match_bigrams.loc[:, match_names_first]
        if isinstance(word_set_first, pd.Series):  # Ensure DataFrame even if one column
            word_set_first = word_set_first.to_frame()

        word_set_names_first = [
            re.sub(rf"^{cnames} ", "", bigram) for bigram in word_set_first.columns
        ]
        word_sum_count_first = word_set_first.sum().sum()

        word_sum_vector_first = np.zeros(word_encoding_length)
        for word, bigram_col in zip(word_set_names_first, word_set_first.columns):
            word_vector = (
                word_df[word]
                if word in word_df.columns
                else np.zeros(word_encoding_length)
            )
            word_count = word_set_first[bigram_col].sum()
            word_sum_vector_first += word_count * word_vector
        E_first = (
            word_sum_vector_first / word_sum_count_first
            if word_sum_count_first != 0
            else np.zeros(word_encoding_length)
        )

        # Match bigrams where 'cnames' is the last word
        match_names_last = [
            bool(re.search(rf" {cnames}$", bigram, flags=re.IGNORECASE))
            for bigram in all_match_bigrams.columns
        ]
        word_set_last = all_match_bigrams.loc[:, match_names_last]
        if isinstance(word_set_last, pd.Series):  # Ensure DataFrame even if one column
            word_set_last = word_set_last.to_frame()

        word_set_names_last = [
            re.sub(rf" {cnames}$", "", bigram) for bigram in word_set_last.columns
        ]
        word_sum_count_last = word_set_last.sum().sum()

        word_sum_vector_last = np.zeros(word_encoding_length)
        for word, bigram_col in zip(word_set_names_last, word_set_last.columns):
            word_vector = (
                word_df[word]
                if word in word_df.columns
                else np.zeros(word_encoding_length)
            )
            word_count = word_set_last[bigram_col].sum()
            word_sum_vector_last += word_count * word_vector
        E_last = (
            word_sum_vector_last / word_sum_count_last
            if word_sum_count_last != 0
            else np.zeros(word_encoding_length)
        )

        # Update feature_df with the computed values
        feature_df[cnames] = np.concatenate((E_first, E_last))

    print("Finished encoding words!")
    return feature_df


with open(
    "/home/vkreschenski/Documents/Privat/Freelancer/similarbooks/data/gutenberg_books/11.txt",
    "r",
    encoding="utf-8",
) as file:
    text = file.read()


def preprocess_text(text):
    # Remove non-ASCII characters
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Remove special characters and numbers
    text = re.sub(r"[,:.{[}\'\"\]]", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"_", "", text)

    # Convert text to lowercase
    text = text.lower()

    # Remove emails and URLs
    text = re.sub(r"\S+@\S+", "", text)  # Emails
    text = re.sub(r"http\S+|www\S+", "", text)  # URLs

    # Remove trailing and leading whitespaces
    text = text.strip()

    return text


cleaned_text = preprocess_text(text)

# Step 1: Split the text into smaller "documents" (e.g., by paragraph or fixed size)
# We can split by paragraphs for now, but you can adjust it as needed.
documents = cleaned_text.split("\n\n")  # Splitting by paragraph

# Step 2: Create a Document-Term Matrix
vectorizer = CountVectorizer(
    min_df=1, stop_words="english"
)  # min_df=50 removes words occurring <50 times
dtm = vectorizer.fit_transform(documents)

# Step 3: Convert the DTM to a DataFrame for easier viewing
dtm_df = pd.DataFrame(dtm.toarray(), columns=vectorizer.get_feature_names_out())
# print(dtm_df.head())  # Display the first few rows of the DTM

# Step 4: Sum up the word occurrences across all documents
word_occurrences = dtm_df.sum(axis=0)

# Display the word occurrences
word_occurrences_sorted = word_occurrences.sort_values(
    ascending=False
)  # Sort by frequency (optional)
# print(word_occurrences_sorted)  # Display the top 10 most frequent words

# Step 1: Create a Bigram Document-Term Matrix
vectorizer_bigram = CountVectorizer(
    ngram_range=(2, 2), min_df=1, stop_words="english"
)  # Set ngram_range=(2, 2) for bigrams
dtm_bigram = vectorizer_bigram.fit_transform(documents)

# Step 2: Convert the Bigram DTM to a DataFrame
dtm_bigram_df = pd.DataFrame(
    dtm_bigram.toarray(), columns=vectorizer_bigram.get_feature_names_out()
)
print(dtm_bigram_df)

# Step 3: Sum up the bigram occurrences across all documents
bigram_occurrences = dtm_bigram_df.sum(axis=0).to_frame().T
print(bigram_occurrences)

# Step 4: Sort and display the top 10 most frequent bigrams
# bigram_occurrences_sorted = bigram_occurrences.sort_values(ascending=False)
# print(bigram_occurrences_sorted)  # Display the top 10 most frequent bigrams

# Step 1: Get the number of columns (terms) from dtm_df
num_columns = dtm_df.shape[1]

# Step 2: Create a DataFrame with 90 rows and random values (between 0.0 and 1.0) for each word
word_df = pd.DataFrame(np.random.uniform(0.0, 1.0, size=(90, num_columns)))

# Step 3: Assign the column names of dtm_df to the new word_df
word_df.columns = dtm_df.columns

print(word_df)

kaski_df = encode_kaski(word_df, bigram_occurrences)
print(kaski_df)
