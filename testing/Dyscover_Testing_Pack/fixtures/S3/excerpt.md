Dyscover parser fixture. Fixture ID: S3-MD. This identifier is test metadata, not a course requirement.
Derived from week-04-lab-student.pdf, PDF page 3. The original PDF remains authoritative.

Week 4 storage stays in-memory; file persistence is Week 5. Core mappings: MethodArgumentNotValidException → 400 VALIDATION_FAILED with field errors; HttpMessageNotReadableException → 400 MALFORMED_REQUEST; OrderNotFoundException → 404 ORDER_NOT_FOUND; DuplicateOrderException → 409 DUPLICATE_ORDER. A catch-all 500 INTERNAL_ERROR handler is a stretch goal.