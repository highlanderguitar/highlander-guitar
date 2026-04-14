import os
import json
import sys
from collections import defaultdict

# ----------------------------------------
# CONFIG
# ----------------------------------------

KEY_CENTER = "G"

NOTE_TO_DEGREE_G = {
    "G": "1",
    "A": "2",
    "B": "3",
    "C": "4",
    "D": "5",
    "E": "6",
    "F#": "7",
    "F": "b7"
}

# ----------------------------------------
# PARSER
# ----------------------------------------

def parse_file(path):
    measures = {}
    current_measure = None

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            # detect measure
            if line.lower().startswith("bar"):
                current_measure = line.replace(":", "")
                measures[current_measure] = []
                continue

            # parse note line
            try:
                time_part, note_part = line.split()
                timestamp = float(time_part)

                note_name, duration = note_part.split(":")
                duration = float(duration)

                measures[current_measure].append({
                    "time": timestamp,
                    "note": note_name,
                    "duration": duration
                })
            except Exception as e:
                print(f"Skipping malformed line: {line}")
                continue

    return measures

# ----------------------------------------
# ANALYSIS
# ----------------------------------------

def analyze(measures):
    results = {}

    for bar, notes in measures.items():
        total_weight = defaultdict(float)
        sequence = []

        for n in notes:
            note = n["note"]
            dur = n["duration"]

            degree = NOTE_TO_DEGREE_G.get(note, "?")

            total_weight[note] += dur

            sequence.append({
                "note": note,
                "degree": degree,
                "duration": dur,
                "time": n["time"]
            })

        # sort by weight
        sorted_weight = sorted(total_weight.items(), key=lambda x: -x[1])

        results[bar] = {
            "sequence": sequence,
            "note_weights": sorted_weight
        }

    return results

# ----------------------------------------
# OUTPUT
# ----------------------------------------

def write_output(data, input_path):
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    project_root = os.path.dirname(os.path.dirname(input_path))
    output_dir = os.path.join(project_root, "parsed_output")

    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{base_name}.json")

    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

    print(f"\nSaved parsed output to:\n{output_path}")


def print_analysis(results):
    for bar, data in results.items():
        print(f"\n=== {bar} ===")

        print("\nSequence:")
        for n in data["sequence"]:
            print(f"{n['time']:>4}  {n['note']:>2} ({n['degree']})  dur={n['duration']}")

        print("\nWeights:")
        for note, weight in data["note_weights"]:
            print(f"{note}: {weight}")

# ----------------------------------------
# MAIN
# ----------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("python score_parser_vertical_slice.py <input_file> [--json]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_json_flag = "--json" in sys.argv

    parsed = parse_file(input_file)
    analyzed = analyze(parsed)

    write_output(analyzed, input_file)

    if output_json_flag:
        print(json.dumps(analyzed, indent=4))
    else:
        print_analysis(analyzed)