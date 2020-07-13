from bs4 import BeautifulSoup


def csrf_token(data):
    soup = BeautifulSoup(data, "html.parser")
    # print(soup.prettify())
    return soup.find(id="csrf_token")["value"]


# pretty-print for debugging purposes
def pp(data):
    print(BeautifulSoup(data, "html.parser").prettify())
