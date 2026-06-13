# TTB Label Assistant - Approach

## Project Goal

The goal of this project is to reduce the amount of manual verification required during alcohol label review by automatically extracting information from label images and comparing it against application data.

Rather than replacing compliance agents, the system is designed to assist reviewers by identifying potential mismatches and highlighting labels that require further inspection.

---

## Design Philosophy

During the discovery interviews, several recurring themes emerged:

* Agents spend significant time performing repetitive field matching.
* OCR accuracy is important, but incorrect approvals are worse than uncertain results.
* Processing time must remain fast enough for practical use.
* The interface should be understandable by users with varying levels of technical experience.
* The system should assist reviewers rather than make final compliance decisions.

Based on these requirements, the application follows a "review-first" approach. When confidence is low or extracted values are uncertain, the system flags the result for manual review instead of attempting to force a match.

---

## System Architecture

The application follows a client-server architecture.

```text
User Upload
      │
      ▼
Next.js Frontend
      │
      ▼
FastAPI Backend
      │
      ▼
OCR Processing
      │
      ▼
Field Extraction
      │
      ▼
Verification Engine
      │
      ▼
Compliance Engine
      │
      ▼
Review Dashboard
```

### Frontend

The frontend was built using:

* Next.js
* React
* TypeScript
* Tailwind CSS

Responsibilities include:

* Label upload
* Application data entry
* Displaying extracted values
* Presenting verification results
* Presenting compliance findings
* Exporting verification reports

---

### Backend

The backend was built using:

* FastAPI
* Python

Responsibilities include:

* Image processing
* OCR execution
* Field extraction
* Similarity comparison
* Compliance validation
* Result generation

---

## OCR Strategy

Tesseract OCR was selected because:

* It is open source.
* It runs locally without external API calls.
* It satisfies environments where outbound network access may be restricted.
* It provides acceptable accuracy for a prototype.

The OCR pipeline:

1. Receive uploaded image.
2. Convert image into OCR-friendly format.
3. Apply OCR using Tesseract.
4. Extract raw text.
5. Parse required label fields.
6. Validate extracted information.

The application attempts to handle common OCR issues such as:

* Rotated labels
* Split text lines
* OCR spelling errors
* Missing punctuation
* Extra whitespace

---

## Field Extraction Approach

The system extracts the following fields:

* Brand Name
* Class/Type
* Alcohol Content
* Net Contents
* Government Warning

Each field uses a combination of:

* Regular expressions
* Text normalization
* OCR cleanup rules
* Similarity matching

This hybrid approach was chosen because alcohol labels generally follow predictable formatting patterns.

---

## Similarity Matching

OCR output is rarely perfect.

To account for OCR imperfections, the system compares values using RapidFuzz similarity scoring.

Examples:

```text
Application: OLD RIVER
OCR: Old River

Result: Match
```

```text
Application: Timber Ridge
OCR: Timber Ridqe

Result: Match (high similarity)
```

```text
Application: Timber Ridge
OCR: Bourbon Whiskey

Result: Needs Review
```

Thresholds are used to determine whether a value should be considered a match or require manual review.

---

## Compliance Validation Approach

The application performs compliance checks separately from field verification.

Field verification answers:

> Does the label match the application?

Compliance validation answers:

> Does the label contain required regulatory elements?

This separation allows the system to identify:

* Missing required fields
* Incorrect application values
* OCR extraction failures
* Potential compliance issues

Current compliance checks include:

* Government warning validation
* Brand name presence
* Class/type presence
* Alcohol content presence
* Net contents presence
* OCR readability checks

---

## Government Warning Validation

The government warning was treated differently from other fields because regulatory wording requirements are strict.

The validation process checks:

1. Presence of the required warning statement.
2. Similarity against the standard federal warning text.
3. Presence of the required "GOVERNMENT WARNING:" header.

The prototype verifies text content but does not currently validate:

* Font size
* Text placement
* Bold formatting
* Label layout requirements

These checks would require computer vision techniques beyond OCR-based text extraction.

---

## Handling Uncertainty

A core design decision was to avoid false positives.

When the system cannot confidently identify a value, it returns:

```text
Needs Review
```

instead of forcing a match.

This mirrors how a compliance reviewer would escalate uncertain cases for manual inspection.

Examples include:

* Poor image quality
* Rotated labels
* Incomplete OCR extraction
* Ambiguous values

---

## Batch Processing

The application supports multiple label uploads in a single session.

This feature was added based on stakeholder feedback describing situations where hundreds of labels may arrive at once from large producers or importers.

Batch processing allows reviewers to evaluate multiple labels without restarting the workflow for each submission.

---

## Performance Considerations

One stakeholder noted that previous scanning solutions became unusable when processing exceeded approximately 30 seconds per label.

The prototype was designed with responsiveness in mind.

Performance optimizations include:

* Local OCR processing
* Lightweight rule-based validation
* Regex-based field extraction
* Fast similarity scoring using RapidFuzz

Typical processing times remain within a few seconds per label.

---

## Tradeoffs

### Chosen

* Fast rule-based extraction
* Local OCR
* Explainable matching logic
* Reviewer-focused workflow

### Not Implemented

* Machine learning models
* Database persistence
* User authentication
* OCR model training
* Advanced computer vision
* Direct COLA integration

These features were intentionally deferred to keep the prototype focused on core validation functionality.

---

## Future Enhancements

Potential future improvements include:

* PaddleOCR integration
* Advanced image preprocessing
* Label orientation correction
* Additional TTB compliance checks
* Historical review tracking
* User accounts and audit logs
* Database-backed storage
* Automated report generation
* Confidence-based review prioritization

---

## Conclusion

The prototype demonstrates how OCR and rule-based validation can reduce repetitive manual review work while preserving human oversight for uncertain or non-compliant cases.

The system prioritizes explainability, speed, and reviewer usability, aligning with the needs identified during stakeholder interviews.
