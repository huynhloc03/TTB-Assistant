"use client";

import { useState } from "react";
import type { BatchResponse, SingleVerificationResult } from "./types";

type ResultPanelProps = {
  batchResult: BatchResponse | null;
  selectedResult: SingleVerificationResult | null;
  selectedResultIndex: number;
  setSelectedResultIndex: (index: number) => void;
};

export default function ResultPanel({
  batchResult,
  selectedResult,
  selectedResultIndex,
  setSelectedResultIndex,
}: ResultPanelProps) {
  const [showOcr, setShowOcr] = useState(false);
  const [selectedExplanation, setSelectedExplanation] =
    useState<string | null>(null);

  const [selectedRawValue, setSelectedRawValue] =
    useState<string | null>(null);
  const passCount =
    batchResult?.results.filter((item) => item.overallStatus === "PASS")
      .length ?? 0;

  const reviewCount =
    batchResult?.results.filter((item) => item.overallStatus !== "PASS")
      .length ?? 0;

  function downloadReport() {
    if (!batchResult) return;

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

    const blob = new Blob([JSON.stringify(batchResult, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `ttb-label-report-${timestamp}.json`;
    link.click();

    URL.revokeObjectURL(url);
  }

  return (
    <section className="rounded-2xl bg-white p-6 shadow-lg">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Verification Dashboard
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Review OCR extraction, field matching, and compliance status.
          </p>
        </div>

        {selectedResult && (
          <span
            className={`rounded-full px-4 py-2 text-sm font-bold ${
              selectedResult.overallStatus === "PASS"
                ? "bg-green-100 text-green-700"
                : selectedResult.overallStatus === "OCR EXTRACTION ONLY"
                  ? "bg-blue-100 text-blue-700"
                  : selectedResult.overallStatus === "ERROR"
                    ? "bg-red-100 text-red-700"
                    : "bg-yellow-100 text-yellow-800"
            }`}
          >
            {selectedResult.overallStatus}
          </span>
        )}
      </div>

      {!batchResult && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
          Upload one or more labels and click Verify Labels to see results.
        </div>
      )}

      {batchResult && (
        <>
          <div
              className="
                mb-5
                grid
                gap-4
                [grid-template-columns:repeat(auto-fit,minmax(160px,1fr))]
              "
            >
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase text-slate-500">
                Files
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-900">
                {batchResult.totalFiles}
              </p>
            </div>

            <div className="rounded-xl bg-green-50 p-4">
              <p className="text-xs font-semibold uppercase text-green-700">
                Pass
              </p>
              <p className="mt-1 text-2xl font-bold text-green-700">
                {passCount}
              </p>
            </div>

            <div className="rounded-xl bg-yellow-50 p-4">
              <p className="text-xs font-semibold uppercase text-yellow-700">
                Review
              </p>
              <p className="mt-1 text-2xl font-bold text-yellow-700">
                {reviewCount}
              </p>
            </div>

            <div className="rounded-xl bg-blue-50 p-4">
              <p className="text-xs font-semibold uppercase text-blue-700">
                Time
              </p>
              <p className="mt-1 text-2xl font-bold text-blue-700">
                {batchResult.totalProcessingTimeSeconds}s
              </p>
            </div>

            <div className="rounded-xl bg-purple-50 p-4">
              <p className="text-xs font-semibold uppercase text-purple-700">
                OCR Confidence
              </p>
              <p className="mt-1 text-2xl font-bold text-purple-700">
                {selectedResult?.ocrConfidence ?? 0}%
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400 hover:shadow-md">
              <button
                type="button"
                onClick={downloadReport}
                className="h-full w-full text-left"
              >
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Export
                </p>

                <p className="mt-1 text-2xl font-bold text-slate-900">
                  ↓
                </p>

                <p className="mt-1 text-xs font-semibold text-slate-700">
                  Download JSON
                </p>
              </button>
            </div>
          </div>

          <div className="mb-5 rounded-xl bg-slate-50 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-900">
              Review Queue
            </p>

            <div className="flex flex-wrap gap-2">
              {batchResult.results.map((item, index) => (
                <button
                  key={`${item.filename}-${index}`}
                  type="button"
                  onClick={() => setSelectedResultIndex(index)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                    selectedResultIndex === index
                      ? "bg-slate-900 text-white"
                      : item.overallStatus === "PASS"
                        ? "bg-green-100 text-green-700"
                        : item.overallStatus === "OCR EXTRACTION ONLY"
                          ? "bg-blue-100 text-blue-700"
                          : item.overallStatus === "ERROR"
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-800"
                  }`}
                >
                  {item.filename || `Label ${index + 1}`} ·{" "}
                  {item.overallStatus}
                </button>
              ))}
            </div>
          </div>

          {selectedResult && (
            <>
              {selectedResult.overallStatus === "ERROR" && (
                <div className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  <p className="font-semibold">File could not be processed.</p>
                  <p>
                    {selectedResult.error || "Unsupported or unreadable file."}
                  </p>
                  <p>{selectedResult.message}</p>
                </div>
              )}

              {selectedResult.parsedFields && (
                <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="font-semibold text-slate-900">
                      Detected Fields
                    </h3>
                    <p className="text-xs text-slate-500">
                      Extracted from OCR
                    </p>
                  </div>

                  <div className="grid gap-3 text-sm text-slate-800 sm:grid-cols-2">
                    <div className="rounded-lg bg-white p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Brand
                      </p>
                      <p className="mt-1 font-semibold text-slate-900">
                        {selectedResult.parsedFields.brandName || "-"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Confidence:{" "}
                        {selectedResult.parsedFieldConfidence?.brandName ?? 0}%
                      </p>
                    </div>

                    <div className="rounded-lg bg-white p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Class/Type
                      </p>
                      <p className="mt-1 font-semibold text-slate-900">
                        {selectedResult.parsedFields.classType || "-"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Confidence:{" "}
                        {selectedResult.parsedFieldConfidence?.classType ?? 0}%
                      </p>
                    </div>

                    <div className="rounded-lg bg-white p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Alcohol Content
                      </p>
                      <p className="mt-1 font-semibold text-slate-900">
                        {selectedResult.parsedFields.alcoholContent || "-"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Confidence:{" "}
                        {selectedResult.parsedFieldConfidence
                          ?.alcoholContent ?? 0}
                        %
                      </p>
                    </div>

                    <div className="rounded-lg bg-white p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Net Contents
                      </p>
                      <p className="mt-1 font-semibold text-slate-900">
                        {selectedResult.parsedFields.netContents || "-"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Confidence:{" "}
                        {selectedResult.parsedFieldConfidence?.netContents ??
                          0}
                        %
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {selectedResult.complianceChecks && (
                <div className="mb-5 rounded-xl border border-slate-200 bg-white p-4">
                  <h3 className="mb-3 font-semibold text-slate-900">
                    Compliance Checks
                  </h3>

                  <div className="grid gap-2 sm:grid-cols-2">
                    {selectedResult.complianceChecks.map((check) => (
                      <div
                        key={check.name}
                        className={`rounded-lg p-3 text-sm font-semibold ${
                          check.passed
                            ? "bg-green-50 text-green-700"
                            : "bg-red-50 text-red-700"
                        }`}
                      >
                        {check.passed ? "✓" : "✕"} {check.name}
                      </div>
                    ))}
                  </div>

                  {selectedResult.complianceChecks
                    .filter((check) => check.name === "Health Warning Statement")
                    .map((check) => (
                      <div
                        key={check.name}
                        className="mt-4 rounded-lg border border-slate-200 bg-slate-950 p-4 text-sm text-slate-100"
                      >
                        <p className="mb-2 font-semibold">
                          Health Warning Details
                        </p>

                        <p className="mb-2 text-slate-300">
                          Similarity: {check.similarity ?? 0}%
                        </p>

                        <div className="grid gap-4">
                          <div>
                            <p className="mb-1 font-semibold text-slate-200">
                              Expected
                            </p>
                            <p className="whitespace-pre-wrap text-slate-300">
                              {check.expected || "-"}
                            </p>
                          </div>

                          <div>
                            <p className="mb-1 font-semibold text-slate-200">
                              Found on Label
                            </p>
                            <p className="whitespace-pre-wrap text-slate-300">
                              {check.found || "-"}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}

              {selectedResult.processingTimeSeconds !== undefined && (
                <p className="mb-4 text-sm text-slate-600">
                  Selected file processing time:{" "}
                  <span className="font-semibold">
                    {selectedResult.processingTimeSeconds}s
                  </span>
                </p>
              )}

              <div className="overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-900">
                    <tr>
                      <th className="p-3">Field</th>
                      <th className="p-3">Expected</th>
                      <th className="p-3">Found</th>
                      <th className="p-3">Similarity</th>
                      <th className="w-32 p-3">Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {(selectedResult.results ?? []).map((item) => (
                      <tr key={item.field} className="border-t border-slate-200">
                        <td className="p-3 font-semibold text-slate-900">
                          {item.field}
                        </td>

                        <td className="p-3 text-slate-700">
                          {item.expected || "-"}
                        </td>

                        <td className="p-3 text-slate-700">
                          {item.foundText || "-"}
                        </td>

                        <td className="p-3 text-slate-700">
                          {item.similarity !== undefined
                            ? `${item.similarity}%`
                            : "-"}
                        </td>

                        <td className="w-32 p-3">
                          <button
                            type="button"
                            onClick={() => {
                              if (item.status !== "Match") {
                                setSelectedExplanation(
                                  item.details ||
                                  `Expected "${item.expected}" but found "${item.foundText}".`
                                );

                                setSelectedRawValue(item.rawFoundText || null);
                              }
                            }}
                            className={`inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold transition-colors duration-200 ${
                              item.status === "Match"
                                ? "bg-green-100 text-green-700"
                                : item.status === "Review"
                                  ? "bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                                  : item.status === "Extracted"
                                    ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                                    : "bg-red-100 text-red-700 hover:bg-red-200"
                            }`}
                          >
                            {item.status}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-6">
                <button
                  type="button"
                  onClick={() => setShowOcr((current) => !current)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  {showOcr ? "Hide OCR Text" : "Show OCR Text"}
                </button>

                {showOcr && (
                  <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-slate-100">
                    {selectedResult.extractedText || ""}
                  </pre>
                )}
              </div>
            </>
          )}
        </>
      )}
      {selectedExplanation && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
          onClick={() => {
            setSelectedExplanation(null);
            setSelectedRawValue(null);
          }}
        >
          <div
            className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">
                Review Explanation
              </h3>

              <button
                type="button"
                onClick={() => {
                  setSelectedExplanation(null);
                  setSelectedRawValue(null);
                }}
                className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-700 hover:bg-slate-200"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <p className="whitespace-pre-wrap text-sm text-slate-700">
                {selectedExplanation}
              </p>

              {selectedRawValue && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Raw OCR Value
                  </p>

                  <p className="font-mono text-sm text-slate-800">
                    {selectedRawValue}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}