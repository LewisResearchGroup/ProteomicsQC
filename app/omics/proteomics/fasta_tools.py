from Bio import SeqIO


def combine_fasta_files(
    fn_a, fn_b, output_fn="combined.faa", prefix_a="REF__", prefix_b="SEARCH__"
):

    records_a = SeqIO.parse(fn_a, "fasta")
    records_b = SeqIO.parse(fn_b, "fasta")

    sequences = []

    for record in records_a:
        record.id = prefix_a + record.id
        sequences.append(record)

    for record in records_b:
        record.id = prefix_b + record.id
        sequences.append(record)

    with open(output_fn, "w") as handle:
        SeqIO.write(sequences, handle, "fasta")
