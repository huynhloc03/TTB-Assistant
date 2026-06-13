export type ResultItem = {
  field: string;
  expected: string;
  foundText?: string;
  found: boolean;
  similarity?: number;
  status: string;
  details: string;
  rawFoundText?: string;
};

export type SingleVerificationResult = {
  overallStatus: string;
  ocrConfidence?: number;
  rotationApplied?: number;
  parsedFields?: {
    brandName?: string;
    classType?: string;
    alcoholContent?: string;
    netContents?: string;
  };
  parsedFieldConfidence?: {
    brandName?: number;
    classType?: number;
    alcoholContent?: number;
    netContents?: number;
  };
  results?: ResultItem[];
  complianceChecks?: ComplianceCheck[];
  extractedText?: string;
  processingTimeSeconds?: number;
  filename?: string;
  error?: string;
  message?: string;
};

export type BatchResponse = {
  totalFiles: number;
  totalProcessingTimeSeconds: number;
  results: SingleVerificationResult[];
};

export type ComplianceCheck = {
  name: string;
  passed: boolean;
  category?: string;
  expected?: string;
  found?: string;
  similarity?: number;
  details?: string;
};