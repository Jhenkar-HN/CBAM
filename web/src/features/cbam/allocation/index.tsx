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
import { useCbamStore } from '@/stores/cbam-store'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StepIndicator } from '../components/step-indicator'

export function AllocationPage() {
  const navigate = useNavigate()
  const allocation = useCbamStore((state) => state.allocation)
  const setAllocation = useCbamStore((state) => state.setAllocation)

  const target = Number(allocation.target_production_tonnes ?? 0)
  const total = Number(allocation.total_facility_production_tonnes ?? 0)
  const alpha = total > 0 ? Math.min(1, target / total) : 0
  const invalid = total > 0 && target > total

  return (
    <>
      <CbamTopBar />
      <Main>
        <StepIndicator current={4} />
        <PageHeader
          title='Mass allocation'
          description='Shared utilities serve several product lines. The allocation factor αₚ apportions facility emissions to the target product family by mass.'
        />

        <div className='grid gap-4 lg:grid-cols-3'>
          <Card className='lg:col-span-2'>
            <CardHeader>
              <CardTitle>Production quantities</CardTitle>
              <CardDescription>
                Use net production for the reporting period, in tonnes.
              </CardDescription>
            </CardHeader>
            <CardContent className='grid gap-4 sm:grid-cols-2'>
              <div className='space-y-2'>
                <Label htmlFor='target'>Target product output (t)</Label>
                <Input
                  id='target'
                  type='number'
                  step='any'
                  value={allocation.target_production_tonnes ?? ''}
                  onChange={(event) => {
                    const value = event.target.value
                    setAllocation({ target_production_tonnes: value === '' ? null : Number(value) })
                  }}
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='total'>Total facility output (t)</Label>
                <Input
                  id='total'
                  type='number'
                  step='any'
                  value={allocation.total_facility_production_tonnes ?? ''}
                  onChange={(event) => {
                    const value = event.target.value
                    setAllocation({ total_facility_production_tonnes: value === '' ? null : Number(value) })
                  }}
                />
              </div>
              {(['fuel', 'electricity'] as const).map((utility) => {
                const key = utility === 'fuel' ? 'fuel_is_shared' : 'electricity_is_shared'
                const value = allocation[key]
                return (
                  <div key={utility} className='space-y-2'>
                    <Label>{utility === 'fuel' ? 'Fuel record covers' : 'Electricity record covers'}</Label>
                    <Select
                      value={value == null ? '' : value ? 'shared' : 'product'}
                      onValueChange={(choice) =>
                        setAllocation(
                          utility === 'fuel'
                            ? { fuel_is_shared: choice === 'shared' }
                            : { electricity_is_shared: choice === 'shared' }
                        )
                      }
                    >
                      <SelectTrigger><SelectValue placeholder='Select from your meter or invoice records' /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value='shared'>Shared installation use</SelectItem>
                        <SelectItem value='product'>Target product line only</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Allocation factor</CardTitle>
              <CardDescription>αₚ = target ÷ facility output</CardDescription>
            </CardHeader>
            <CardContent className='space-y-3'>
              <p className='text-4xl font-bold tabular-nums'>
                {alpha.toFixed(4)}
              </p>
              <p className='text-sm text-muted-foreground'>
                {target.toLocaleString()} t of {total.toLocaleString()} t
              </p>
              {invalid && (
                <p className='text-sm text-destructive'>
                  Target output cannot exceed total facility output.
                </p>
              )}
              {total <= 0 && (
                <p className='text-sm text-destructive'>
                  Total facility output must be greater than zero.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className='mt-6 flex justify-end gap-2'>
          <Button
            onClick={() => {
              if (allocation.fuel_is_shared === null || allocation.electricity_is_shared === null) {
                toast.error('Choose the allocation basis shown by both utility records.')
                return
              }
              if (!(target > 0) || !(total > 0) || invalid) {
                toast.error('Enter valid target and total production quantities.')
                return
              }
              toast.success('Allocation saved.')
              void navigate({ to: '/passport' })
            }}
            disabled={total <= 0 || invalid}
          >
            Save and calculate
          </Button>
        </div>
      </Main>
    </>
  )
}
