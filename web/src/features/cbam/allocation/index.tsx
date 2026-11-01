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
import { Switch } from '@/components/ui/switch'
import { Main } from '@/components/layout/main'
import { useCbamStore } from '@/stores/cbam-store'
import { CbamTopBar } from '../components/cbam-top-bar'
import { PageHeader } from '../components/page-header'
import { StepIndicator } from '../components/step-indicator'

export function AllocationPage() {
  const navigate = useNavigate()
  const allocation = useCbamStore((state) => state.allocation)
  const setAllocation = useCbamStore((state) => state.setAllocation)

  const target = Number(allocation.target_production_tonnes) || 0
  const total = Number(allocation.total_facility_production_tonnes) || 0
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
                  value={allocation.target_production_tonnes}
                  onChange={(event) =>
                    setAllocation({
                      target_production_tonnes: Number(event.target.value),
                    })
                  }
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='total'>Total facility output (t)</Label>
                <Input
                  id='total'
                  type='number'
                  step='any'
                  value={allocation.total_facility_production_tonnes}
                  onChange={(event) =>
                    setAllocation({
                      total_facility_production_tonnes: Number(
                        event.target.value
                      ),
                    })
                  }
                />
              </div>
              <div className='flex items-center justify-between gap-4 rounded-md border p-3 sm:col-span-2'>
                <div className='space-y-0.5'>
                  <Label htmlFor='shared-energy'>
                    Apply allocation to shared utilities
                  </Label>
                  <p className='text-xs text-muted-foreground'>
                    When off, fuel and electricity are treated as fully
                    attributable to the target product.
                  </p>
                </div>
                <Switch
                  id='shared-energy'
                  checked={allocation.apply_allocation_to_shared_energy}
                  onCheckedChange={(checked) =>
                    setAllocation({ apply_allocation_to_shared_energy: checked })
                  }
                />
              </div>
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
