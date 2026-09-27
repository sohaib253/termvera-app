/** File types the API can read. Mirrors SUPPORTED_EXTENSIONS in
 *  apps/api/app/services/extraction.py; the server re-checks every upload,
 *  so this list only saves the user a round trip on an obvious mismatch. */
export const SUPPORTED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".docm",
  ".doc",
  ".rtf",
  ".odt",
  ".txt",
  ".png",
  ".jpg",
  ".jpeg",
  ".tif",
  ".tiff",
];

export const UPLOAD_ACCEPT = SUPPORTED_EXTENSIONS.join(",");

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

export const SUPPORTED_FORMATS_HINT =
  "PDF (scanned or digital), Word (.docx, .doc), RTF, ODT, TXT, or scanned images. Up to 50MB.";

/** Why this file can't be uploaded, or null if it looks fine. */
export function validateUploadFile(file: File): string | null {
  const dot = file.name.lastIndexOf(".");
  const extension = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!SUPPORTED_EXTENSIONS.includes(extension)) {
    return `"${file.name}" is not a supported file type. Upload a ${SUPPORTED_FORMATS_HINT}`;
  }
  if (file.size === 0) return `"${file.name}" is empty.`;
  if (file.size > MAX_UPLOAD_BYTES) return `"${file.name}" is larger than the 50MB limit.`;
  return null;
}

/** "OGDCL_Sand-Trap_Contract 2014.pdf" -> "OGDCL Sand Trap Contract 2014":
 *  a reasonable default name so a dropped file needs no typing. */
export function nameFromFilename(filename: string): string {
  const dot = filename.lastIndexOf(".");
  const stem = dot > 0 ? filename.slice(0, dot) : filename;
  return stem.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
