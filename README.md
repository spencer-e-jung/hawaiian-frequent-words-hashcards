# Hawaii Frequent Words Hashcards

A script to manage a ʻōlelo Hawaiʻi spaced repetition deck [for a fork](https://github.com/spencer-e-jung/hashcards) of [hashcards](https://github.com/eudoxia0/hashcards). Support for adding new entries from the dictionary, either by number of new words, or by explicitly naming the word, and removing entries from the deck by word, number to remove from the end.

```
usage: __main__.py [-h] [--remove REMOVE | --entries ENTRIES] out

Modifies a hashcard deck of ʻōlelo Hawaiʻi words.

positional arguments:
  out                   output file.

options:
  -h, --help            show this help message and exit
  --remove, -r REMOVE   number of entries or word to remove from the deck
  --entries, -e ENTRIES
                        number of entries or word to add from the dictionary
```
