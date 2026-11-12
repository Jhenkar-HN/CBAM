import { useState } from 'react'
import { BookOpen, Loader2, Search } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Main } from '@/components/layout/main'
import { API_URL, queryRegulatory, type RAGQueryResponse } from '@/lib/cbam-api'
import { useCbamStore } from '@/stores/cbam-store'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StatusBadge } from '../components/status-badge'

const EXAMPLES = [
  'What are the rules for precursor emissions for steel fasteners under CN 7318?',
  'How is electricity consumption reported for an installation in India?',
  'When may default values be used instead of actual emissions?',
]

export function AssistantPage() {
  const cnCode = useCbamStore((state) => state.workspace.cn_code)
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<RAGQueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ask = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    try {
      setResult(await queryRegulatory(trimmed, 3, cnCode))
    } catch (cause) {
      setResult(null)
      setError(
        cause instanceof Error ? cause.message : 'Regulatory query failed.'
      )
    } finally {
      setLoading(false)
    }
  }

  const guardrail =
    result?.answer.toLowerCase().includes('no official regulatory source') ?? false

  return (
    <>
      <CbamTopBar />
      <Main>
        <PageHeader
          title='Regulatory assistant'
          description='Searches the configured source documents and returns retrieved passages with their recorded source details.'
        >
          <StatusBadge label={`CN ${cnCode}`} variant='neutral' />
        </PageHeader>

        <div className='grid gap-4 lg:grid-cols-3'>
          <Card className='lg:col-span-2'>
            <CardHeader>
              <CardTitle>Ask a question</CardTitle>
              <CardDescription>
                Retrieval runs over the local corpus in{' '}
                <code>data/regulatory_docs/</code>.
              </CardDescription>
            </CardHeader>
            <CardContent className='space-y-3'>
              <Textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                rows={3}
                placeholder='e.g. How are precursor emissions attributed to complex goods?'
              />
              <Button
                onClick={() => void ask(query)}
                disabled={loading || !query.trim()}
              >
                {loading ? (
                  <Loader2 className='size-4 animate-spin' />
                ) : (
                  <Search className='size-4' />
                )}
                Search regulations
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Try an example</CardTitle>
            </CardHeader>
            <CardContent className='space-y-2'>
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type='button'
                  className='w-full rounded-md border p-2 text-left text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground'
                  onClick={() => {
                    setQuery(example)
                    void ask(example)
                  }}
                >
                  {example}
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {error && (
          <Alert variant='destructive' className='mt-4'>
            <AlertTitle>Assistant unavailable</AlertTitle>
            <AlertDescription>
              {error}
              <span className='mt-1 block text-xs'>
                The RAG endpoint needs the backend at {API_URL} and the FAISS
                index built from <code>data/regulatory_docs/</code>.
              </span>
            </AlertDescription>
          </Alert>
        )}

        {result && (
          <Card className='mt-4'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <BookOpen className='size-4' />
                Answer
              </CardTitle>
              <CardDescription>{result.query}</CardDescription>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div
                className={
                  guardrail
                    ? 'rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100'
                    : 'rounded-md bg-muted/40 p-4 text-sm leading-relaxed'
                }
              >
                {result.answer}
              </div>

              <div>
                <p className='mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase'>
                  Citations
                </p>
                {result.citations.length === 0 ? (
                  <p className='text-sm text-muted-foreground'>
                    No official source met the similarity threshold.
                  </p>
                ) : (
                  <ul className='space-y-3'>
                    {result.citations.map((citation, index) => (
                      <li
                        key={`${citation.document_title}-${index}`}
                        className='rounded-md border p-3'
                      >
                        <div className='flex flex-wrap items-center justify-between gap-2'>
                          <p className='text-sm font-semibold'>
                            {citation.document_title}
                          </p>
                          <StatusBadge
                            label={`score ${citation.score.toFixed(3)}`}
                            variant='neutral'
                          />
                        </div>
                        <p className='text-xs text-muted-foreground'>
                          {citation.section_reference} ·{' '}
                          {citation.publication_year ?? 'Publication year not recorded'}
                        </p>
                        {citation.source_url && (
                          <a
                            className='mt-1 block text-xs text-primary underline'
                            href={citation.source_url}
                            target='_blank'
                            rel='noreferrer'
                          >
                            Open source document
                          </a>
                        )}
                        <blockquote className='mt-2 border-s-2 ps-3 text-xs italic'>
                          {citation.excerpt}
                        </blockquote>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </Main>
    </>
  )
}
