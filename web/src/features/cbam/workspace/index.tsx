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
  '7318 15 95',
  '7318 16 00',
]

const PRODUCT_FAMILIES = ['Steel Fasteners']

export function WorkspacePage() {
  const navigate = useNavigate()
  const workspace = useCbamStore((state) => state.workspace)
  const setWorkspace = useCbamStore((state) => state.setWorkspace)
  const [form, setForm] = useState(workspace)

  const update = (key: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [key]: value }))

  const save = () => {
    if (
      !form.company_name.trim() || !form.installation_name.trim() ||
      !form.installation_id.trim() || !form.country.trim() ||
      !form.cn_code.trim() || !form.target_product_family.trim() ||
      !form.reporting_period.trim() || !form.fuel_name.trim() ||
      !form.precursor_cn_code.trim() || !form.precursor_material_name.trim() ||
      !form.precursor_country.trim()
    ) {
      toast.error('Complete the workspace fields using your actual installation and supplier records.')
      return
    }
    setWorkspace({ ...form, includes_indirect: true })
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
                  placeholder='Enter the exporting company name'
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='installation_name'>Installation name</Label>
                <Input
                  id='installation_name'
                  value={form.installation_name}
                  onChange={(e) => update('installation_name', e.target.value)}
                  placeholder='Enter the factory or installation name'
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='installation_id'>Installation ID</Label>
                <Input
                  id='installation_id'
                  value={form.installation_id}
                  onChange={(e) => update('installation_id', e.target.value)}
                  placeholder='Enter the actual installation ID'
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='country'>Country</Label>
                <Input
                  id='country'
                  value={form.country}
                  onChange={(e) => update('country', e.target.value)}
                  placeholder='Enter the country of origin'
                />
              </div>
              <div className='space-y-2'>
                <Label>Reporting period</Label>
                <Input
                  value={form.reporting_period}
                  onChange={(e) => update('reporting_period', e.target.value)}
                  placeholder='Enter the reporting period from your records'
                />
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
                  <SelectTrigger className='w-full'>
                    <SelectValue placeholder='Select the product family' />
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
                  <SelectTrigger className='w-full'>
                    <SelectValue placeholder='Select the actual product CN code' />
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
              <div className='space-y-2'>
                <Label>Fuel type shown on your fuel record</Label>
                <Select
                  value={form.fuel_name}
                  onValueChange={(value) => update('fuel_name', value)}
                >
                  <SelectTrigger className='w-full'><SelectValue placeholder='Select the recorded fuel type' /></SelectTrigger>
                  <SelectContent>
                    {['Furnace Oil', 'Diesel (HSD)', 'Natural Gas', 'LPG'].map((fuel) => (
                      <SelectItem key={fuel} value={fuel}>{fuel}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className='space-y-2'>
                <Label>Precursor CN code from supplier record</Label>
                <Input
                  value={form.precursor_cn_code}
                  onChange={(e) => update('precursor_cn_code', e.target.value)}
                  placeholder='Enter the supplier material CN code'
                />
              </div>
              <div className='space-y-2'>
                <Label>Precursor material name from supplier record</Label>
                <Input
                  value={form.precursor_material_name}
                  onChange={(e) => update('precursor_material_name', e.target.value)}
                  placeholder='Enter the material name shown by the supplier'
                />
              </div>
              <div className='space-y-2'>
                <Label>Precursor country of origin</Label>
                <Input
                  value={form.precursor_country}
                  onChange={(e) => update('precursor_country', e.target.value)}
                  placeholder='Enter the origin shown in the supplier record'
                />
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
