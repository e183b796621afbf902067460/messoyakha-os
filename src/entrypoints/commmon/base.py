from re import findall


def findall_prefixes(strings: list[str]) -> list[str]:
    pattern: str = r"\b([a-zA-Z]+_\d+)_(?:open|high|low|close)\b"

    prefixes: list[str] = []
    for string in strings:
        match: list[str] = findall(pattern=pattern, string=string)
        if match and match[0] not in prefixes:
            prefixes.append(match[0])
    return prefixes
