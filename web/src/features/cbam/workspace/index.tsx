import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Main } from '@/components/layout/main'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StepIndicator } from '../components/step-indicator'
import { useCbamStore } from '@/stores/cbam-store'

const CN_CODES = [
  '7318 15 82',
  '7318 15 89',
  '7318 16 90',
  '7318 11 00',
  '7318 21 00',
]

const PRODUCT_FAMILIES = ['Steel Fasteners', 'Steel Wire Rod', 'Steel Bars']

const PERIODS = [
  'Q1 2026 (Jan-Mar)',
  'Q2 2026 (Apr-Jun)',
  'Q3 2026 (Jul-Sep)',
  'Q4 2026 (Oct-Dec)',
  '2026 (Annual)',
]

export function WorkspacePage() {
  const navigate = useNavigate()
  const workspace = useCbamStore((state) => state.workspace)
  const setWorkspace = useCbamStore((state) => state.setWorkspace)
  const [form, setForm] = useState(workspace)

  const update = (key: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [key]: value }))

  const save = () => {
    if (!form.company_name.trim() || !form.installation_id.trim()) {
      toast.error('Company name and installation ID are required.')
      return
    }
    setWorkspace(form)
    toast.success('Workspace saved.')
    void navigate({ to: '/upload' })
  }

  return (
    <>
      <CbamTopBar />
      <Main>
        <StepIndicator current={1} />
        <PageHeader
          title='Setup workspace'
          description='Define the reporting entity, installation, and target product family before ingesting records.'
        />

        <div className='grid gap-4 lg:grid-cols-3'>
          <Card className='lg:col-span-2'>
            <CardHeader>
              <CardTitle>Installation profile</CardTitle>
              <CardDescription>
                These details appear in the passport header and the audit
                ledger.
              </CardDescription>
            </CardHeader>
            <CardContent className='grid gap-4 sm:grid-cols-2'>
              <div className='space-y-2 sm:col-span-2'>
                <Label htmlFor='company_name'>Company name</Label>
                <Input
                  id='company_name'
                  value={form.company_name}
                  onChange={(e) => update('company_name', e.target.value)}
                  placeholder='Apex Fasteners Pvt Ltd'
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='installation_name'>Installation name</Label>
                <Input
                  id='installation_name'
                  value={form.installation_name}
                  onChange={(e) => update('installation_name', e.target.value)}
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='installation_id'>Installation ID</Label>
                <Input
                  id='installation_id'
                  value={form.installation_id}
                  onChange={(e) => update('installation_id', e.target.value)}
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='country'>Country</Label>
                <Input
                  id='country'
                  value={form.country}
                  onChange={(e) => update('country', e.target.value)}
                />
              </div>
              <div className='space-y-2'>
                <Label>Reporting period</Label>
                <Select
                  value={form.reporting_period}
                  onValueChange={(value) => update('reporting_period', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder='Select a period' />
                  </SelectTrigger>
                  <SelectContent>
                    {PERIODS.map((period) => (
                      <SelectItem key={period} value={period}>
                        {period}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Target product</CardTitle>
              <CardDescription>
                The pilot vertical slice covers steel fasteners under CN 7318.
              </CardDescription>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div className='space-y-2'>
                <Label>Product family</Label>
                <Select
                  value={form.target_product_family}
                  onValueChange={(value) =>
                    update('target_product_family', value)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRODUCT_FAMILIES.map((family) => (
                      <SelectItem key={family} value={family}>
                        {family}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className='space-y-2'>
                <Label>CN code</Label>
                <Select
                  value={form.cn_code}
                  onValueChange={(value) => update('cn_code', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CN_CODES.map((code) => (
                      <SelectItem key={code} value={code}>
                        {code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className='text-xs text-muted-foreground'>
                Scope 2 is included when the CN code requires indirect
                emissions reporting.
              </p>
            </CardContent>
          </Card>
        </div>

        <div className='mt-6 flex justify-end'>
          <Button onClick={save}>Save and continue</Button>
        </div>
      </Main>
    </>
  )
}
