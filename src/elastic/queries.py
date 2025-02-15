

unique_course_values = {
  "size": "0",
  "aggs": {
    "unique_values": {
      "terms": {
        "field": "course.keyword"
      }
    }
  }
}
