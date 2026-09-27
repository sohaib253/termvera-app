"use client";

import { FileUp } from "lucide-react";
import { useRef, useState } from "react";

import { cn } from "@/lib/cn";
import {
  formatFileSize,
  SUPPORTED_FORMATS_HINT,
  UPLOAD_ACCEPT,
  validateUploadFile,
} from "@/lib/upload";

interface FileDropzoneProps {
  /** Called with the files that passed validation. */
  onFiles: (files: File[]) => void;
  multiple?: boolean;
  disabled?: boolean;
  /** Currently chosen file, shown in place of the prompt. */
  selected?: File | null;
  title?: string;
  hint?: string;
  compact?: boolean;
  className?: string;
}

/** Click-to-browse or drag-and-drop file picker. Unsupported files are
 *  rejected here with a message rather than after a round trip, and the
 *  hidden input is cleared after each pick so choosing the same file again
 *  still fires. */
export function FileDropzone({
  onFiles,
  multiple = false,
  disabled = false,
  selected = null,
  title,
  hint = SUPPORTED_FORMATS_HINT,
  compact = false,
  className,
}: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const accept = (list: FileList | null) => {
    if (!list || list.length === 0) return;
    const files = Array.from(list).slice(0, multiple ? undefined : 1);
    const problems = files.map(validateUploadFile).filter((p): p is string => p !== null);
    const valid = files.filter((f) => validateUploadFile(f) === null);
    setError(problems.length > 0 ? problems.join(" ") : null);
    if (valid.length > 0) onFiles(valid);
  };

  const open = () => {
    if (!disabled) inputRef.current?.click();
  };

  return (
    <div className={className}>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onClick={open}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            open();
          }
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragOver={(e) => {
          // Required for the browser to allow a drop here at all.
          e.preventDefault();
          e.dataTransfer.dropEffect = disabled ? "none" : "copy";
        }}
        onDragLeave={(e) => {
          // dragleave also fires when moving over a child element.
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) accept(e.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer items-center gap-3 rounded-md border border-dashed px-4 transition-colors",
          compact ? "py-3" : "py-6",
          dragging
            ? "border-primary bg-[var(--status-neutral-bg)]"
            : "border-[var(--border)] hover:bg-gray-50",
          disabled && "cursor-not-allowed opacity-60 hover:bg-transparent",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        )}
      >
        <FileUp className="h-5 w-5 shrink-0 text-muted-foreground" />
        <div className="min-w-0 text-sm">
          {selected ? (
            <>
              <p className="truncate font-medium text-foreground">{selected.name}</p>
              <p className="text-muted-foreground">
                {formatFileSize(selected.size)}. Drop or click to choose a different file.
              </p>
            </>
          ) : (
            <>
              <p className="font-medium text-foreground">
                {dragging
                  ? "Drop to upload"
                  : (title ?? (multiple ? "Drag files here or click to browse" : "Drag a file here or click to browse"))}
              </p>
              <p className="text-muted-foreground">{hint}</p>
            </>
          )}
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={UPLOAD_ACCEPT}
        multiple={multiple}
        className="hidden"
        onChange={(e) => {
          accept(e.target.files);
          e.target.value = "";
        }}
      />
      {error && (
        <p className="mt-2 text-xs text-[var(--status-critical-fg)]" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
