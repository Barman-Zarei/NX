import sys

def classify(n: int | None) -> str:
    match n:
        case None:
            return "none"
        case 0:
            return "zero"
        case _:
            return "num:" + str(n)

def main():
    name = "prefix-demo".removeprefix("prefix-")
    print("mytool", name, classify(0), classify(7), classify(None))
    return 0

if __name__ == "__main__":
    sys.exit(main())
