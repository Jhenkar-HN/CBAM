import { useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { FileUp, Loader2, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Main } from '@/components/layout/main'
import { API_URL, uploadDocument } from '@/lib/cbam-api'
import { useCbamStore } from '@/stores/cbam-store'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StepIndicator } from '../components/step-indicator'

const ACCEPTED = '.pdf,.png,.jpg,.jpeg,.csv,.xlsx'

export function UploadPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const documents = useCbamStore((state) => state.documents)
  const workspace = useCbamStore((state) => state.workspace)
  const addDocument = useCbamStore((state) => state.addDocument)
  const removeDocument = useCbamStore((state) => state.removeDocument)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    if (!workspace.installation_id.trim()) {
      setError('Save the actual workspace and installation ID before uploading records.')
      return
    }
    setBusy(true)
    setError(null)
    for (const file of Array.from(files)) {
      try {
        const result = await uploadDocument(file, workspace.installation_id)
        addDocument({ ...result, file_size_bytes: file.size })
        toast.success(
          `${result.filename}: ${result.extracted_fields.length} field(s) extracted.`
        )
      } catch (cause) {
        const message =
          cause instanceof Error ? cause.message : 'Upload failed.'
        setError(`${file.name}: ${message}`)
        toast.error(`${file.name}: ${message}`)
      }
    }
    setBusy(false)
    if (inputRef.current) inputRef.current.value = ''
  }

  const rows = Object.values(documents)

  return (
    <>
      <CbamTopBar />
      <Main>
        <StepIndicator current={2} />
        <PageHeader
          title='Upload records'
          description='Electricity bills, fuel invoices, precursor declarations, and production logs. Each file is hashed with SHA-256 and parsed for activity data.'
        >
          {rows.length > 0 && (
            <Button asChild>
              <Link to='/review'>Review extraction</Link>
            </Button>
          )}
        </PageHeader>

        {error && (
          <Alert variant='destructive' className='mb-4'>
            <AlertTitle>Upload problem</AlertTitle>
            <AlertDescription>
              {error}
              <span className='mt-1 block text-xs'>
                Check that the backend is running at {API_URL}.
              </span>
            </AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Source documents</CardTitle>
            <CardDescription>
              PDF, PNG, JPG, CSV, or XLSX. Upload each activity type as its own
              file so extraction stays unambiguous.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <label
              htmlFor='record-upload'
              className='flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 px-6 py-10 text-center transition-colors hover:bg-muted/50'
            >
              {busy ? (
                <Loader2 className='size-6 animate-spin text-muted-foreground' />
              ) : (
                <FileUp className='size-6 text-muted-foreground' />
              )}
              <span className='text-sm font-medium'>
                {busy ? 'Parsing documents…' : 'Click to choose files'}
              </span>
              <span className='text-xs text-muted-foreground'>
                Multiple files allowed. Nothing leaves this machine except the
                request to your local backend.
              </span>
              <input
                ref={inputRef}
                id='record-upload'
                type='file'
                multiple
                accept={ACCEPTED}
                className='sr-only'
                disabled={busy}
                onChange={(event) => void handleFiles(event.target.files)}
              />
            </label>
          </CardContent>
        </Card>

        <Card className='mt-4'>
          <CardHeader>
            <CardTitle>Evidence ledger</CardTitle>
            <CardDescription>
              {rows.length === 0
                ? 'No documents ingested yet.'
                : `${rows.length} document(s) ingested.`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {rows.length === 0 ? (
              <p className='text-sm text-muted-foreground'>
                Upload a record to populate the ledger.
              </p>
            ) : (
              <div className='overflow-x-auto'>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>File</TableHead>
                      <TableHead>SHA-256</TableHead>
                      <TableHead className='text-right'>Pages</TableHead>
                      <TableHead className='text-right'>Fields</TableHead>
                      <TableHead className='text-right'>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((document) => (
                      <TableRow key={document.document_hash}>
                        <TableCell className='font-medium'>
                          {document.filename}
                        </TableCell>
                        <TableCell className='font-mono text-xs'>
                          {document.document_hash.slice(0, 12)}…
                        </TableCell>
                        <TableCell className='text-right'>
                          {document.page_count}
                        </TableCell>
                        <TableCell className='text-right'>
                          {document.extracted_fields.length}
                        </TableCell>
                        <TableCell className='text-right'>
                          <Button
                            variant='ghost'
                            size='icon'
                            aria-label={`Remove ${document.filename}`}
                            onClick={() => removeDocument(document.document_hash)}
                          >
                            <Trash2 className='size-4' />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </Main>
    </>
  )
}
