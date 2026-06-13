"use client";

import { useState } from "react";
import ApplicationForm from "./components/ApplicationForm";
import ResultPanel from "./components/ResultPanel";
import type { BatchResponse, SingleVerificationResult } from "./components/types";

export type ApplicationData = {
  brandName: string;
  classType: string;
  alcoholContent: string;
  netContents: string;
};

const emptyApplicationData: ApplicationData = {
  brandName: "",
  classType: "",
  alcoholContent: "",
  netContents: "",
};

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [applicationDataList, setApplicationDataList] = useState<ApplicationData[]>([]);
  const [selectedResultIndex, setSelectedResultIndex] = useState(0);
  const [batchResult, setBatchResult] = useState<BatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedResult = batchResult?.results[selectedResultIndex] ?? null;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const newlySelectedFiles = Array.from(e.target.files ?? []);

    if (newlySelectedFiles.length === 0) return;

    setFiles((currentFiles) => {
      const existingNames = new Set(currentFiles.map((file) => file.name));

      const uniqueNewFiles = newlySelectedFiles.filter(
        (file) => !existingNames.has(file.name)
      );

      return [...currentFiles, ...uniqueNewFiles];
    });

    setImagePreviews((currentPreviews) => [
      ...currentPreviews,
      ...newlySelectedFiles.map((file) => URL.createObjectURL(file)),
    ]);

    setApplicationDataList((currentData) => [
      ...currentData,
      ...newlySelectedFiles.map(() => ({ ...emptyApplicationData })),
    ]);

    setBatchResult(null);
    setError("");

    e.target.value = "";
  }

  function handleRemoveFile(indexToRemove: number) {
    setFiles((current) => current.filter((_, index) => index !== indexToRemove));
    setImagePreviews((current) =>
      current.filter((_, index) => index !== indexToRemove)
    );
    setApplicationDataList((current) =>
      current.filter((_, index) => index !== indexToRemove)
    );

    setBatchResult(null);

    setSelectedResultIndex((currentIndex) => {
      if (currentIndex === indexToRemove) return 0;
      if (currentIndex > indexToRemove) return currentIndex - 1;
      return currentIndex;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBatchResult(null);

    if (files.length === 0) {
      setError("Please upload at least one label image.");
      return;
    }

    try {
      setLoading(true);
      const startTime = performance.now();

      const verificationPromises = files.map(async (file, index) => {
        const formData = new FormData();

        formData.append("file", file);
        formData.append(
          "applicationData",
          JSON.stringify(applicationDataList[index])
        );

        const API_URL =
          process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

        const response = await fetch(`${API_URL}/verify`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Verification failed for ${file.name}`);
        }

        return response.json();
      });

      const results = await Promise.all(verificationPromises);

      const totalTime = Math.round((performance.now() - startTime) / 10) / 100;

      setBatchResult({
        totalFiles: files.length,
        totalProcessingTimeSeconds: totalTime,
        results,
      });
    } catch {
      setError(
        "Could not verify labels. Make sure the backend is running and re-select the files if needed."
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-100 to-slate-200 p-6">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900">TTB Label Assistant</h1>
          <p className="mt-2 text-lg text-slate-600">
            OCR-powered alcohol beverage label analysis and TTB compliance assistance
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-2">
          <ApplicationForm
            files={files}
            imagePreviews={imagePreviews}
            applicationDataList={applicationDataList}
            selectedResultIndex={selectedResultIndex}
            loading={loading}
            error={error}
            onFileChange={handleFileChange}
            onRemoveFile={handleRemoveFile}
            onSubmit={handleSubmit}
            setSelectedResultIndex={setSelectedResultIndex}
            setApplicationDataList={setApplicationDataList}
          />

          <ResultPanel
            batchResult={batchResult}
            selectedResult={selectedResult}
            selectedResultIndex={selectedResultIndex}
            setSelectedResultIndex={setSelectedResultIndex}
          />
        </div>
      </div>
    </main>
  );
}