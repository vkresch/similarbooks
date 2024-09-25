import requests


def get_isbn_from_title_author_year(title, author=None, year=None):
    # Construct the query string for the Google Books API
    query = f"intitle:{title}"

    if author:
        query += f"+inauthor:{author}"

    if year:
        query += f"+inpublisheddate:{year}"  # The year is generally associated with the publisher's release date

    # Google Books API URL with query parameters
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query}

    # Make a request to the API
    response = requests.get(url, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        books = response.json()

        # Check if there are any books returned
        if "items" in books:
            for book in books["items"]:
                # Try to extract the ISBN from industryIdentifiers
                if "industryIdentifiers" in book["volumeInfo"]:
                    for identifier in book["volumeInfo"]["industryIdentifiers"]:
                        if identifier["type"] == "ISBN_10":
                            return identifier["identifier"]
        return "No ISBN found for the given title."
    else:
        return f"Error fetching data from Google Books API. Status code: {response.status_code}"


# Example usage:
title = "Der Graf von Monte-Christo"
author = "Alexandre Dumas"
year = "2008"

isbn = get_isbn_from_title_author_year(title, author, year)
print(f"ISBN for '{title}' by {author} (published in {year}): {isbn}")
