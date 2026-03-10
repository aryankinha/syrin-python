"use client";

export interface AttachmentData {
  url: string;
  type: string;
  contentType?: string;
}

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  attachments?: AttachmentData[];
  onAttachmentsChange?: (attachments: AttachmentData[]) => void;
  maxFileSizeMB?: number;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = "Type a message…",
  attachments = [],
  onAttachmentsChange,
  maxFileSizeMB = 10,
}: ChatInputProps) {
  const maxBytes = maxFileSizeMB * 1024 * 1024;

  const addImage = (url: string, contentType = "image/png") => {
    if (!onAttachmentsChange) return;
    const type = contentType.startsWith("image/") ? "image" : "file";
    onAttachmentsChange([...attachments, { url, type, contentType }]);
  };

  const removeAttachment = (idx: number) => {
    if (!onAttachmentsChange) return;
    onAttachmentsChange(attachments.filter((_, i) => i !== idx));
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const items = e.clipboardData?.items;
    if (!items || !onAttachmentsChange) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (!file || file.size > maxBytes) continue;
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = reader.result as string;
          addImage(dataUrl, file.type);
        };
        reader.readAsDataURL(file);
        break;
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length || !onAttachmentsChange) return;
    for (const file of Array.from(files)) {
      if (file.size > maxBytes) continue;
      const isImage = file.type.startsWith("image/");
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        addImage(dataUrl, file.type);
      };
      reader.readAsDataURL(file);
    }
    e.target.value = "";
  };

  return (
    <div className="input-row multimodality">
      {attachments.length > 0 && (
        <div className="attachment-preview">
          {attachments.map((a, i) =>
            a.type === "image" ? (
              <div key={i} className="attachment-thumb">
                <img src={a.url} alt="" />
                {onAttachmentsChange && (
                  <button
                    type="button"
                    className="attachment-remove"
                    onClick={() => removeAttachment(i)}
                    aria-label="Remove"
                  >
                    ×
                  </button>
                )}
              </div>
            ) : null
          )}
        </div>
      )}
      <div className="input-group">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onPaste={handlePaste}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
        />
        <label className="file-upload-btn" title="Attach image or file">
          <input
            type="file"
            accept="image/*,application/pdf"
            onChange={handleFileSelect}
            disabled={disabled}
            aria-label="Attach file"
          />
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </label>
        <button onClick={onSend} disabled={disabled}>
          Send
        </button>
      </div>
    </div>
  );
}
