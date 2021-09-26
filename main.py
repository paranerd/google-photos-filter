import argparse

from filters.no_album import NoAlbumFilter

filters = [
    NoAlbumFilter,
]


def main(filter_name):
    for filter in filters:
        if filter.name == filter_name:
            f = filter()
            f.filter()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--filter')
    arguments, _ = parser.parse_known_args()

    filter = arguments.filter

    main(filter)
