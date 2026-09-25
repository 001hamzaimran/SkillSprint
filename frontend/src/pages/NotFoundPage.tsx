import { Link } from 'react-router';
import { SearchX, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function NotFoundPage() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg border-muted/20">
        <CardContent className="pt-10 pb-10 px-8 flex flex-col items-center text-center space-y-6">
          <div className="w-16 h-16 bg-muted/10 rounded-full flex items-center justify-center mb-2">
            <SearchX className="w-8 h-8 text-muted-foreground" />
          </div>
          
          <Badge variant="warning" className="px-3 py-1 text-xs uppercase tracking-wider font-mono">
            404 Error
          </Badge>
          
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight text-ink">Let's resolve this.</h1>
            <p className="text-muted">
              The page you are looking for does not exist or has been moved.
            </p>
          </div>
          
          <Button asChild className="mt-4" size="lg">
            <Link to="/">
              Back to overview <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default NotFoundPage;

