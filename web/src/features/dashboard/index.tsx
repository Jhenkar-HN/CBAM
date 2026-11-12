import { Link } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Main } from '@/components/layout/main'
import { CbamTopBar } from '@/features/cbam/components/cbam-top-bar'

export function Dashboard() {
  return (
    <>
      <CbamTopBar />
      <Main>
        <div className='mx-auto max-w-3xl py-12'>
          <Card>
            <CardHeader>
              <CardTitle>CBAM Emissions Passport</CardTitle>
              <CardDescription>
                No passport data is shown until you enter an installation and upload its source records.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link to='/workspace'>Set up a workspace</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </Main>
    </>
  )
}
