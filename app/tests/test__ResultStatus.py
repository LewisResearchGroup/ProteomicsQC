from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from maxquant.models import Pipeline, RawFile, Result
from project.models import Project
from user.models import User


class ResultStatusTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tester-status@example.com", password="pass1234"
        )
        self.project = Project.objects.create(
            name="Status Project", description="Status test project", created_by=self.user
        )
        contents_mqpar = b"<mqpar></mqpar>"
        contents_fasta = b">protein\nSEQUENCE"
        self.pipeline = Pipeline.objects.create(
            name="status-pipe",
            project=self.project,
            created_by=self.user,
            fasta_file=SimpleUploadedFile("status_fasta.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("status_mqpar.xml", contents_mqpar),
            rawtools_args="-p -q -x",
        )
        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("status_case.raw", b"..."),
            created_by=self.user,
        )
        self.result = Result.objects.get(raw_file=self.raw_file)

    def _write_file(self, fn, text):
        fn = Path(fn)
        fn.parent.mkdir(parents=True, exist_ok=True)
        fn.write_text(text, encoding="utf-8")

    def test_maxquant_error_overrides_done_marker(self):
        # Mark RawTools stages as done so overall status depends on MaxQuant.
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")

        # MaxQuant wrote time.txt but also a non-empty error file.
        self._write_file(self.result.output_dir_maxquant / "time.txt", "00:05.00")
        self._write_file(
            self.result.output_dir_maxquant / "maxquant.err",
            "System.Exception: Your fully qualified path of raw file is too long.",
        )

        self.assertEqual(self.result.maxquant_status, "failed")
        self.assertEqual(self.result.overall_status, "failed")

    def test_rawtools_metrics_error_overrides_done_markers(self):
        # Mark MaxQuant and RawTools QC as done so overall status depends on RawTools metrics.
        self._write_file(self.result.output_dir_maxquant / "time.txt", "00:05.00")
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")

        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools / "rawtools_metrics.err",
            "RawTools metrics failed",
        )

        self.assertEqual(self.result.rawtools_metrics_status, "failed")
        self.assertEqual(self.result.overall_status, "failed")

    def test_rawtools_qc_error_overrides_done_marker(self):
        # Mark MaxQuant and RawTools metrics as done so overall status depends on RawTools QC.
        self._write_file(self.result.output_dir_maxquant / "time.txt", "00:05.00")
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )

        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")
        self._write_file(
            self.result.output_dir_rawtools_qc / "rawtools_qc.err",
            "RawTools QC failed",
        )

        self.assertEqual(self.result.rawtools_qc_status, "failed")
        self.assertEqual(self.result.overall_status, "failed")

    @patch.object(Result, "_task_state", return_value="SUCCESS")
    def test_rawtools_success_state_with_outputs_is_done(self, _mock_task_state):
        self.result.rawtools_metrics_task_id = "fake-metrics-task"
        self.result.rawtools_qc_task_id = "fake-qc-task"
        self.result.save(
            update_fields=["rawtools_metrics_task_id", "rawtools_qc_task_id"]
        )

        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")
        self._write_file(self.result.output_dir_rawtools / "rawtools_metrics.err", "")
        self._write_file(self.result.output_dir_rawtools_qc / "rawtools_qc.err", "")

        self.assertEqual(self.result.rawtools_metrics_status, "done")
        self.assertEqual(self.result.rawtools_qc_status, "done")

    @patch.object(Result, "_task_state", return_value="PENDING")
    def test_rawtools_pending_state_with_outputs_is_done(self, _mock_task_state):
        self.result.rawtools_metrics_task_id = "fake-metrics-task"
        self.result.rawtools_qc_task_id = "fake-qc-task"
        self.result.save(
            update_fields=["rawtools_metrics_task_id", "rawtools_qc_task_id"]
        )

        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")

        self.assertEqual(self.result.rawtools_metrics_status, "done")
        self.assertEqual(self.result.rawtools_qc_status, "done")

    def test_maxquant_success_phrase_in_out_file_marks_done_first(self):
        # RawTools done so overall depends on MaxQuant.
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")

        # Strong success indicator in maxquant.out should win.
        self._write_file(
            self.result.output_dir_maxquant / "maxquant.out",
            "...\nFinish writing tables\n...",
        )
        self._write_file(
            self.result.output_dir_maxquant / "maxquant.err",
            "error text that would otherwise mark failed",
        )

        self.assertEqual(self.result.maxquant_status, "done")
        self.assertEqual(self.result.overall_status, "done")

    def test_maxquant_fatal_error_markers_override_success_phrase(self):
        # RawTools done so overall depends on MaxQuant.
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")

        self._write_file(
            self.result.output_dir_maxquant / "maxquant.out",
            "...\nFinish writing tables\n...",
        )
        self._write_file(
            self.result.output_dir_maxquant / "maxquant.err",
            "System.Exception: path too long",
        )

        self.assertEqual(self.result.maxquant_status, "failed")
        self.assertEqual(self.result.overall_status, "failed")

    def test_stage_error_details_exposes_failed_stage_excerpt(self):
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(
            self.result.output_dir_rawtools
            / f"{self.raw_file.name}_Ms2_TIC_chromatogram.txt",
            "ok",
        )
        self._write_file(self.result.output_dir_rawtools_qc / "QcDataTable.csv", "ok")
        self._write_file(
            self.result.output_dir_maxquant / "maxquant.err",
            "Unhandled Exception:\nSystem.Exception: Your fully qualified path of raw file is too long.",
        )

        details = self.result.stage_error_details
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["stage"], "maxquant")
        self.assertIn("Unhandled Exception", details[0]["message"])
