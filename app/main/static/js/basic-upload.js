$(function () {
  let shouldRefreshAfterUpload = false;
  let uploadSeq = 0;

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function showUploadFeedback(kind, text) {
    const $feedback = $("#upload-feedback");
    if (!$feedback.length) return;
    const klass = kind === "error" ? "upload-feedback-error" : "upload-feedback-success";
    $feedback.html("<div class='upload-feedback-message " + klass + "'>" + escapeHtml(text) + "</div>");
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes < 0) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
  }

  function updateQueueCount() {
    const $rows = $("#upload-queue-body tr[data-upload-id]");
    $("#upload-queue-count").text($rows.length + " file" + ($rows.length === 1 ? "" : "s"));
    if ($rows.length === 0) {
      if (!$("#upload-queue-empty").length) {
        $("#upload-queue-body").append("<tr id='upload-queue-empty'><td colspan='4'>No active uploads.</td></tr>");
      }
    } else {
      $("#upload-queue-empty").remove();
    }
  }

  function createQueueRow(file) {
    const uploadId = "u" + (++uploadSeq);
    const safeName = escapeHtml(file.name || "unnamed.raw");
    const sizeText = formatBytes(file.size);
    const html =
      "<tr data-upload-id='" + uploadId + "'>" +
      "<td title='" + safeName + "'><span class='upload-queue-name'>" + safeName + "</span></td>" +
      "<td>" + sizeText + "</td>" +
      "<td><div class='upload-queue-progress'><span class='upload-queue-progress-fill' style='width:0%'></span></div><span class='upload-queue-progress-text'>0%</span></td>" +
      "<td><span class='upload-queue-status status-queued'>queued</span></td>" +
      "</tr>";
    $("#upload-queue-empty").remove();
    $("#upload-queue-body").prepend(html);
    updateQueueCount();
    return uploadId;
  }

  function setQueueProgress(uploadId, percent) {
    const value = Math.max(0, Math.min(100, percent || 0));
    const $row = $("#upload-queue-body tr[data-upload-id='" + uploadId + "']");
    $row.find(".upload-queue-progress-fill").css("width", value + "%");
    $row.find(".upload-queue-progress-text").text(value + "%");
  }

  function setQueueStatus(uploadId, text, statusClass) {
    const $row = $("#upload-queue-body tr[data-upload-id='" + uploadId + "']");
    const $status = $row.find(".upload-queue-status");
    $status.removeClass("status-queued status-running status-done status-failed");
    $status.addClass(statusClass || "status-queued");
    $status.text(text);
  }

  function prependRunButton(name, resultUrl, resultPk) {
    const $list = $("#mq-runs-list");
    if (!$list.length || !resultUrl) return false;
    const normalized = String(name).toLowerCase();
    const alreadyExists = $list.find("tr[data-run-name='" + normalized + "']").length > 0;
    if (alreadyExists) return false;

    const $row = $("<tr></tr>").attr("data-run-name", normalized);
    $row.append($("<td></td>").append($("<span></span>").addClass("mq-run-name").text(name)));
    $row.append($("<td></td>").append($("<span></span>").addClass("status-pill status-queued").text("queued")));
    $row.append($("<td></td>").append($("<span></span>").addClass("status-pill status-queued").text("queued")));
    $row.append($("<td></td>").append($("<span></span>").addClass("status-pill status-queued").text("queued")));
    $row.append($("<td></td>").append($("<span></span>").addClass("status-pill status-queued").text("queued")));
    $row.append(
      $("<td></td>").append(
        $("<a></a>").attr("href", resultUrl).addClass("mq-open-link").text("Open")
      )
    );
    const cancelBase = String($list.data("cancelRunBase") || "");
    let cancelUrl = "";
    if (cancelBase && resultPk) {
      cancelUrl = cancelBase.replace(/\/0\/?$/, "/" + String(resultPk));
    }
    const $cancelBtn = $("<button></button>")
      .attr("type", "button")
      .addClass("mq-cancel-btn")
      .text("Cancel");
    if (cancelUrl) {
      $cancelBtn.attr("data-url", cancelUrl);
    } else {
      $cancelBtn.prop("disabled", true);
    }
    $row.append($("<td></td>").append($cancelBtn));

    $list.prepend($row);
    $("#mq-runs-empty-row").remove();
    return true;
  }

  $(".js-upload-photos").click(function () {
    $("#fileupload").click();
  });

  $("#fileupload").fileupload({
    dataType: 'json',
    sequentialUploads: true,  /* 1. SEND THE FILES ONE BY ONE */
    add: function (e, data) {
      if (data.files && data.files.length > 0) {
        data.uploadId = createQueueRow(data.files[0]);
      }
      if (data.uploadId) {
        setQueueStatus(data.uploadId, "uploading", "status-running");
      }
      data.submit();
    },
    start: function (e) {  /* 2. WHEN THE UPLOADING PROCESS STARTS, SHOW THE MODAL */
      shouldRefreshAfterUpload = false;
    },
    stop: function (e) {  /* 3. WHEN THE UPLOADING PROCESS FINALIZE, HIDE THE MODAL */
      if (shouldRefreshAfterUpload) {
        setTimeout(function () {
          window.location.reload();
        }, 700);
      }
    },
    progressall: function (e, data) {  /* 4. UPDATE THE PROGRESS BAR */
      // Global modal progress intentionally disabled.
      // Per-file progress is shown in the upload queue table.
    },
    progress: function (e, data) {
      if (!data.uploadId) return;
      const progress = parseInt((data.loaded / data.total) * 100, 10);
      setQueueProgress(data.uploadId, progress);
      setQueueStatus(data.uploadId, "uploading", "status-running");
    },
    done: function (e, data) {
      if (data.result.is_valid) {
        const inserted = prependRunButton(data.result.name, data.result.result_url, data.result.result_pk);
        shouldRefreshAfterUpload = true;
        if (data.uploadId) {
          setQueueProgress(data.uploadId, 100);
          if (data.result.already_exists) {
            setQueueStatus(data.uploadId, "already exists", "status-done");
          } else {
            setQueueStatus(data.uploadId, "completed", "status-done");
          }
        }
        if (data.result.already_exists) {
          showUploadFeedback(
            "success",
            data.result.restored_result
              ? "File already existed. Restored its run entry and updated the list."
              : inserted
                ? "File already existed. Added existing run entry to the list."
                : "File already existed. The page will refresh to sync the run list."
          );
        } else {
          showUploadFeedback(
            "success",
            inserted
              ? "Upload received and run added to the list."
              : "Upload received. The page will refresh to sync the run list."
          );
        }
      } else {
        if (data.uploadId) {
          setQueueStatus(data.uploadId, "failed", "status-failed");
        }
        showUploadFeedback("error", "Upload failed. Please try again.");
      }
    },
    fail: function (e, data) {
      if (data && data.uploadId) {
        setQueueStatus(data.uploadId, "failed", "status-failed");
      }
      let message = "Upload failed due to a server error.";
      const jqXHR = data && data.jqXHR ? data.jqXHR : null;
      if (jqXHR && jqXHR.responseJSON && jqXHR.responseJSON.error) {
        message = jqXHR.responseJSON.error;
      } else if (jqXHR && jqXHR.status === 409) {
        message = "Upload conflict detected. The file may already exist in this pipeline.";
      }
      showUploadFeedback("error", message);
    }

  });

  updateQueueCount();
});
