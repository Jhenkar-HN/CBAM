import { cn } from '@/lib/utils'

type FooterProps = React.ComponentProps<'footer'>

export function Footer({ className, ...props }: FooterProps) {
  return (
    <footer
      className={cn(
        'text-muted-foreground mt-auto shrink-0 border-t px-4 py-4 text-center text-sm',
        className
      )}
      {...props}
    >
      <span>
        CBAM-Ready Emissions Passport &middot; decision-support prototype. Does
        not certify emissions or replace an accredited verifier.
      </span>
    </footer>
  )
}
