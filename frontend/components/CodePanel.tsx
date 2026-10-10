'use client';
import Editor from '@monaco-editor/react';

// Read-only in comprehension mode: the candidate explains the code, never edits it.
export default function CodePanel({ code, language = 'python' }: { code: string; language?: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <Editor
        height="340px"
        language={language}
        value={code}
        theme="vs-dark"
        options={{
          readOnly: true, minimap: { enabled: false }, fontSize: 13.5,
          scrollBeyondLastLine: false, lineNumbers: 'on', padding: { top: 14, bottom: 14 },
          renderLineHighlight: 'none', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        }}
      />
    </div>
  );
}
