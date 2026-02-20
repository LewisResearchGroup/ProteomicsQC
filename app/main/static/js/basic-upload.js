$(function () {
  let shouldRefreshAfterUpload = false;

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

  function prependRunButton(name, resultUrl) {
    const $list = $("#mq-runs-list");
    if (!$list.length || !resultUrl) return false;
    const alreadyExists = $list.find("button").filter(function () {
      return $(this).attr("data-run-name") === name;
    }).length > 0;
    if (alreadyExists) return false;

    const $button = $("<button></button>")
      .addClass("btn full_width upload-new-run")
      .attr("data-run-name", name)
      .text(name);
    const $anchor = $("<a></a>").attr("href", resultUrl).append($button);

    $list.prepend($anchor);
    $("#mq-runs-empty").remove();
    return true;
  }

  $(".js-upload-photos").click(function () {
    $("#fileupload").click();
  });

  $("#fileupload").fileupload({
    dataType: 'json',
    sequentialUploads: true,  /* 1. SEND THE FILES ONE BY ONE */
    start: function (e) {  /* 2. WHEN THE UPLOADING PROCESS STARTS, SHOW THE MODAL */
      shouldRefreshAfterUpload = false;
      $("#modal-progress").modal("show");
    },
    stop: function (e) {  /* 3. WHEN THE UPLOADING PROCESS FINALIZE, HIDE THE MODAL */
      $("#modal-progress").modal("hide");
      if (shouldRefreshAfterUpload) {
        setTimeout(function () {
          window.location.reload();
        }, 700);
      }
    },
    progressall: function (e, data) {  /* 4. UPDATE THE PROGRESS BAR */
      var progress = parseInt(data.loaded / data.total * 100, 10);
      var strProgress = progress + "%";
      $(".progress-bar").css({"width": strProgress});
      $(".progress-bar").text(strProgress);
    },
    done: function (e, data) {
      if (data.result.is_valid) {
        const inserted = prependRunButton(data.result.name, data.result.result_url);
        shouldRefreshAfterUpload = true;
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
        showUploadFeedback("error", "Upload failed. Please try again.");
      }
    },
    fail: function () {
      showUploadFeedback("error", "Upload failed due to a server error.");
    }

  });

});
