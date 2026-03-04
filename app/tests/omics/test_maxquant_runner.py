import os
import pytest
from pathlib import Path as P

from omics.proteomics.maxquant.MaxquantRunner import MaxquantRunner


PATH = P("tests/omics/data")


class TestMaxquantRunner:
    @pytest.fixture
    def mqpar_path(self):
        return PATH / "maxquant" / "tmt11" / "mqpar" / "mqpar.xml"

    @pytest.fixture
    def fake_fasta(self, tmp_path):
        """Create a minimal FASTA file for testing."""
        fasta = tmp_path / "minimal.faa"
        fasta.write_text(">sp|TEST|TEST_HUMAN Test protein\nMKWVTFISLLLLFSSAYS\n")
        return fasta

    @pytest.fixture
    def fake_raw(self, tmp_path):
        """Create a fake RAW file for testing."""
        raw = tmp_path / "fake.raw"
        raw.write_bytes(b"FAKE RAW FILE CONTENT")
        return raw

    def test_missing_faa_raises_exception(self, mqpar_path):
        fn_faa = PATH / "fasta" / "does-not-exist.faa"
        with pytest.raises(AssertionError):
            MaxquantRunner(
                fasta_file=fn_faa,
                mqpar_file=mqpar_path,
                maxquantcmd="echo",
            )

    def test_missing_mqpar_raises_exception(self, fake_fasta):
        fn_mqp = PATH / "does-not-exist.xml"
        with pytest.raises(AssertionError):
            MaxquantRunner(
                fasta_file=fake_fasta,
                mqpar_file=fn_mqp,
                maxquantcmd="echo",
            )

    def test_input_files_created(self, tmp_path, mqpar_path, fake_fasta, fake_raw):
        run_dir = tmp_path / "run"
        out_dir = tmp_path / "out"

        mq = MaxquantRunner(
            fasta_file=fake_fasta,
            mqpar_file=mqpar_path,
            run_dir=run_dir,
            out_dir=out_dir,
            add_uuid_to_rundir=False,
            add_raw_name_to_outdir=False,
            maxquantcmd="echo",
        )

        mq.run(fake_raw, run=False)

        files_generated = [
            (run_dir / "run.sbatch").is_file(),
            (run_dir / "fake.raw").is_file(),
            (run_dir / "mqpar.xml").is_file(),
        ]

        assert all(files_generated), f"Missing files: {files_generated}"

    def test_runner_creates_directories(self, tmp_path, mqpar_path, fake_fasta, fake_raw):
        run_dir = tmp_path / "run"
        out_dir = tmp_path / "out"

        mq = MaxquantRunner(
            fasta_file=fake_fasta,
            mqpar_file=mqpar_path,
            run_dir=run_dir,
            out_dir=out_dir,
            add_uuid_to_rundir=False,
            add_raw_name_to_outdir=False,
            maxquantcmd="echo",
        )

        mq.run(fake_raw, run=False)

        assert run_dir.is_dir()
        assert out_dir.is_dir()

    def test_rerun_false_skips_existing(self, tmp_path, mqpar_path, fake_fasta, fake_raw):
        run_dir = tmp_path / "run"
        out_dir = tmp_path / "out"

        # Create directories to simulate existing run
        run_dir.mkdir(parents=True)
        out_dir.mkdir(parents=True)

        mq = MaxquantRunner(
            fasta_file=fake_fasta,
            mqpar_file=mqpar_path,
            run_dir=run_dir,
            out_dir=out_dir,
            add_uuid_to_rundir=False,
            add_raw_name_to_outdir=False,
            maxquantcmd="echo",
        )

        result = mq.run(fake_raw, rerun=False)
        assert result is None

    def test_cold_run_does_not_create_files(self, tmp_path, mqpar_path, fake_fasta, fake_raw):
        run_dir = tmp_path / "run"
        out_dir = tmp_path / "out"

        mq = MaxquantRunner(
            fasta_file=fake_fasta,
            mqpar_file=mqpar_path,
            run_dir=run_dir,
            out_dir=out_dir,
            add_uuid_to_rundir=False,
            add_raw_name_to_outdir=False,
            maxquantcmd="echo",
        )

        mq.run(fake_raw, cold_run=True)

        assert not run_dir.exists()
        assert not out_dir.exists()

    def test_add_raw_name_to_outdir(self, tmp_path, mqpar_path, fake_fasta, fake_raw):
        run_dir = tmp_path / "run"
        out_dir = tmp_path / "out"

        mq = MaxquantRunner(
            fasta_file=fake_fasta,
            mqpar_file=mqpar_path,
            run_dir=run_dir,
            out_dir=out_dir,
            add_uuid_to_rundir=False,
            add_raw_name_to_outdir=True,
            maxquantcmd="echo",
        )

        mq.run(fake_raw, run=False)

        # Output should be in out/fake/
        assert (out_dir / "fake").is_dir()
