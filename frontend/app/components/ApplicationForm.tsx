"use client";

import { useState } from "react";
import Image from "next/image";
import type { ApplicationData } from "../page";




type ApplicationFormProps = {
  files: File[];
  imagePreviews: string[];
  applicationDataList: ApplicationData[];
  selectedResultIndex: number;
  loading: boolean;
  error: string;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (index: number) => void;
  onSubmit: (e: React.FormEvent) => void;
  setSelectedResultIndex: (index: number) => void;
  setApplicationDataList: React.Dispatch<React.SetStateAction<ApplicationData[]>>;
};

export default function ApplicationForm({
  files,
  imagePreviews,
  applicationDataList,
  selectedResultIndex,
  loading,
  error,
  onFileChange,
  onRemoveFile,
  onSubmit,
  setSelectedResultIndex,
  setApplicationDataList,
}: ApplicationFormProps) {
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null);

  const selectedApplicationData = applicationDataList[selectedResultIndex] ?? {
    brandName: "",
    classType: "",
    alcoholContent: "",
    netContents: "",
  };

  function updateSelectedField(field: keyof ApplicationData, value: string) {
    setApplicationDataList((current) =>
      current.map((item, index) =>
        index === selectedResultIndex ? { ...item, [field]: value } : item
      )
    );
  }

  return (
    <section className="rounded-2xl bg-white p-6 shadow-lg">
      <h2 className="mb-4 text-xl font-bold text-slate-900">
        Application Data
      </h2>

      <form onSubmit={onSubmit} className="grid gap-5">
        <div>
          <label className="block text-sm font-semibold text-slate-900">
            Label Images
          </label>

          <input
            type="file"
            multiple
            accept="image/png,image/jpeg,image/jpg"
            onChange={onFileChange}
            className="mt-2 block w-full rounded-lg border border-slate-300 bg-white p-3 text-slate-900 file:mr-4 file:rounded-md file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-white hover:file:bg-slate-700"
          />

          {files.length > 0 && (
            <p className="mt-2 text-sm text-slate-600">
              {files.length} file{files.length > 1 ? "s" : ""} selected
            </p>
          )}
        </div>

        {imagePreviews.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-900">
              Select a label to enter its application data
            </p>

            <div className="grid gap-3 sm:grid-cols-2">
              {imagePreviews.map((preview, index) => (
                <div
                    key={preview}
                    className={`group relative rounded-lg border bg-white p-2 text-left transition ${
                    selectedResultIndex === index
                      ? "border-slate-900 ring-2 ring-slate-300"
                      : "border-slate-300 hover:border-slate-500"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onRemoveFile(index)}
                    aria-label={`Remove ${files[index]?.name ?? "label"}`}
                    className="
                      absolute right-2 top-2 z-10
                      flex h-5 w-5 items-center justify-center
                      rounded-full
                      bg-black/70
                      text-[10px] text-white
                      opacity-0
                      transition-all
                      duration-200
                      group-hover:opacity-100
                    "
                  >
                    ×
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedResultIndex(index)}
                    className="block w-full text-left"
                  >
                    <div
                      className="relative h-40 w-full overflow-hidden rounded-md bg-white cursor-zoom-in"
                      onDoubleClick={() => setEnlargedImage(preview)}
                    >
                      <Image
                        src={preview}
                        alt={`Uploaded label preview ${index + 1}`}
                        fill
                        className="object-contain"
                      />
                    </div>

                    <p className="mt-2 truncate text-xs font-medium text-slate-700">
                      {files[index]?.name}
                    </p>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {files.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-900">
              Application data for{" "}
              <span className="text-slate-700">
                {files[selectedResultIndex]?.name}
              </span>
            </p>

            <div className="grid gap-4">
              <input
                placeholder="Brand Name"
                value={selectedApplicationData.brandName}
                onChange={(e) => updateSelectedField("brandName", e.target.value)}
                className="rounded-lg border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />

              <input
                placeholder="Class/Type"
                value={selectedApplicationData.classType}
                onChange={(e) => updateSelectedField("classType", e.target.value)}
                className="rounded-lg border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />

              <input
                placeholder="Alcohol Content"
                value={selectedApplicationData.alcoholContent}
                onChange={(e) =>
                  updateSelectedField("alcoholContent", e.target.value)
                }
                className="rounded-lg border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />

              <input
                placeholder="Net Contents"
                value={selectedApplicationData.netContents}
                onChange={(e) => updateSelectedField("netContents", e.target.value)}
                className="rounded-lg border border-slate-300 bg-white p-3 text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 p-3 text-sm font-medium text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-slate-900 px-5 py-3 font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          {loading ? "Verifying..." : "Verify Labels"}
        </button>
      </form>
      {enlargedImage && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
        onClick={() => setEnlargedImage(null)}
      >
        <div
          className="relative max-h-[90vh] w-full max-w-4xl rounded-xl bg-white p-4"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={() => setEnlargedImage(null)}
            className="absolute right-3 top-3 z-10 rounded-full bg-black px-3 py-1 text-sm font-bold text-white"
          >
            X
          </button>

          <div className="relative h-[80vh] w-full">
            <Image
              src={enlargedImage}
              alt="Enlarged label preview"
              fill
              className="object-contain"
            />
          </div>
        </div>
      </div>
    )}
    </section>
  );
}