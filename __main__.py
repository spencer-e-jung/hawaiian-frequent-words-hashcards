import re
import mmap
import argparse
from pathlib import Path
from itertools import islice
from typing import Callable, Generator, List, Optional
from platformdirs import user_config_dir

CFG_DIR  = Path(user_config_dir('hawaiian-frequent-words'))
CFG_FILE = CFG_DIR / 'state.txt'

CLOZE_START = "||"
CLOZE_END = "||"

DICT = Path("HawFreqToEng.txt")

def mmap_lines(mm: mmap.mmap, predicate: Callable[[str], bool]) -> Generator[str]:
    start = 0
    while True:
        nl = mm.find(b'\n', start)
        if nl == -1:
            if start < len(mm):
                if predicate(mm[start:].decode("utf-8")):
                    yield mm[start:].decode("utf-8")
            break
        if predicate(mm[start : nl+1].decode("utf-8")):
            yield mm[start : nl+1].decode("utf-8")
        start = nl + 1

def load() -> int:
    try:
        with open(CFG_FILE) as f:
            return int(f.read())
    except FileNotFoundError:
        return 0
    
def save(number: int) -> None:
    """Persist the number of entries from the dictionary saved."""
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CFG_FILE, "w") as f:
        f.write(str(number))

def lookup_word(word: str) -> List[str]:
    """Looks up a dictionary entry for word in HawFreqToEng.txt"""
    with open(DICT, encoding='utf-8') as f, \
        mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        for line in mmap_lines(mm, bool):
            try:
                w, _ = line.split('\t', 1)
            except ValueError:
                continue
            if w == word:
                return [line.rstrip()]
        raise ValueError(f"word {word} not found.")

def lookup_next_most_frequent(count: int, out: Path) -> List[str]:
    """Looks up the next dictionary entries to be added from HawFreqToEng.txt
Skips words already in the hashcards deck."""
    # We scan the entire out hashcard deck for every word to add.
    # This is not particularly efficient.
    def is_line_word_in_out(line: str) -> bool:
        """Returns True if the word in the dictionary line is in the out hashcard deck."""
        w, _ = line.split('\t', 1)
        word_entry_re = re.compile(
                fr'^C:\|\|{re.escape(w)}\|\|.*?(\n\n---\n\n)'.encode(),
                flags=re.MULTILINE | re.DOTALL
        )
        with open(out, encoding='utf-8') as f, \
            mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            try:
                next(word_entry_re.finditer(mm))
                return False
            except StopIteration:
                return True
             
    cursor = load()

    with open(DICT, encoding='utf-8') as f, \
        mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        try:
            return list(
                islice(mmap_lines(mm, is_line_word_in_out), cursor, cursor + count)
            )
        except StopIteration:
            raise ValueError(f'file has fewer than {cursor + count} lines')

def remove_word(word: str, out: Path) -> None:
    """Removes a word entry from the out hashcard deck."""
    word_entry_re = re.compile(
        fr'^C:\|\|{re.escape(word)}\|\|.*?(\n\n---\n\n)'.encode(),
        flags=re.MULTILINE | re.DOTALL
    )

    with open(out, "r+b") as f, mmap.mmap(f.fileno(), 0) as mm:
        entries = word_entry_re.finditer(mm)
        count = 0
        for entry in entries:
            if entry:
                start, end = entry.span()
                tail_len = len(mm) - end
                mm.move(start, end, tail_len)
                mm.flush()
                f.truncate(start + tail_len)
                count = count + 1
            else:
                raise ValueError("word {word} not found.")
        save(load() - count)
    
def remove_least_frequent(count: int, out: Path) -> None:
    """Removes count word entries from the end of the out hashcard deck."""
    entry_re = re.compile(rb'(?=^C:.*?\n\n---\n\n)', flags=re.MULTILINE | re.DOTALL)
    with open(out, "r+b") as f, mmap.mmap(f.fileno(), 0) as mm:
        starts = [m.start() for m in entry_re.finditer(mm)]
        if len(starts) <= count:
            mm.resize(0)
        else:
            mm.resize(starts[-count])
    save(load() - count)

def add(entries: List[str], out: Path) -> None:
    """Adds entries to the out hashcard deck giving different definitions a newline."""
    def split_on_definition_number (d):
        d = re.sub(r' (\d+\. )', r'\n\1', d)    
        d = re.sub(r'\t', r'\n', d)
        return d[:-1]
    for entry in entries:
        with open(out, "a") as f:
            w, d = entry.split('\t', 1)
            d = split_on_definition_number(d)           
            f.write("C:")
            f.write(CLOZE_START + w + CLOZE_END + "\n")
            f.write(CLOZE_START + d + CLOZE_END)
            f.write("\n\n---\n\n")
    save(load() + len(entries))

def main():
    parser = argparse.ArgumentParser(description="Modifies a hashcard deck of ʻōlelo Hawaiʻi words.")
    group = parser.add_mutually_exclusive_group()
    parser.add_argument("out", type=Path, help="output file.")
    group.add_argument("--remove", "-r", type=str, help="number of entries or word to remove from the deck")
    group.add_argument("--entries", "-e", type=str, help="number of entries or word to add from the dictionary")
    args = parser.parse_args()

    out = Path(args.out).expanduser().resolve()

    if args.remove:
        try:
            count = int(args.remove)
            remove_least_frequent(count, out)
        except ValueError:
            remove_word(args.remove, out)
            
    if args.entries:
        try:
            count = int(args.entries)
            lines = lookup_next_most_frequent(count, out)
            add(lines, out)
        except ValueError:
            lines = lookup_word(args.entries)
            add(lines, out)

if __name__ == "__main__":
    main()

