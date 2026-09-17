import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { useEffect } from 'react'

function markdownToHtml(markdown: string): string {
  return markdown
    .split('\n')
    .map((line) => {
      if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`
      if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`
      if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`
      if (line.startsWith('- ')) return `<li>${line.slice(2)}</li>`
      if (line.startsWith('> ')) return `<blockquote>${line.slice(2)}</blockquote>`
      if (line.trim() === '') return '<p></p>'
      if (line.startsWith('|')) return `<p class="table-line">${line}</p>`
      return `<p>${line.replace(/`([^`]+)`/g, '<code>$1</code>')}</p>`
    }).join('')
}

export function ReportEditor({ markdown, onChange }: { markdown: string; onChange?: (html: string) => void }) {
  const editor = useEditor({
    extensions: [StarterKit, Placeholder.configure({ placeholder: '生成报告后可在这里补充研究说明…' })],
    content: markdownToHtml(markdown),
    onUpdate: ({ editor: current }) => onChange?.(current.getHTML()),
    editorProps: { attributes: { class: 'report-editor', 'aria-label': '报告编辑器' } },
  })
  useEffect(() => {
    if (editor && markdown) editor.commands.setContent(markdownToHtml(markdown))
  }, [editor, markdown])
  return <EditorContent editor={editor} />
}
