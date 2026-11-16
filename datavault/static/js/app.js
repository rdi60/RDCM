document.addEventListener("DOMContentLoaded", function () {
  var topicSelect = document.getElementById("id_topic");
  var subtopicSelect = document.getElementById("id_subtopic");
  if (!topicSelect || !subtopicSelect) return;

  function filterSubtopics() {
    var topicId = topicSelect.value;
    var currentValue = subtopicSelect.value;
    var hasMatch = false;
    Array.prototype.forEach.call(subtopicSelect.options, function (option) {
      if (!option.value) {
        option.hidden = false;
        return;
      }
      var matches = !topicId || option.getAttribute("data-topic") === topicId;
      option.hidden = !matches;
      if (matches && option.value === currentValue) hasMatch = true;
    });
    if (!hasMatch) subtopicSelect.value = "";
  }

  topicSelect.addEventListener("change", filterSubtopics);
  filterSubtopics();
});
