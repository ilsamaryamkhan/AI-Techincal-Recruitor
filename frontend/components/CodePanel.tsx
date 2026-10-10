'use client';
import Editor from '@monaco-editor/react';
// Read-only in comprehension mode: candidate explains, does not edit.
export default function CodePanel({ code, language='python' }: { code: string; language?: string }) {
  return <Editor height="360px" language={language} value={code} options={{ readOnly: true, minimap: { enabled: false } }} />;
}
