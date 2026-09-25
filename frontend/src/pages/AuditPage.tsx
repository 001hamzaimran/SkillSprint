import React, { useState, useEffect } from 'react';
import { History, SearchX, ChevronDown, ChevronUp } from 'lucide-react';
import { formatDateTime, truncateId, cn } from '@/lib/utils';
import api from '@/lib/api';

import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        const data = await api.get('audit').json<{ events: any[] }>();
        setEvents(data.events || []);
      } catch (err) {
        setEvents([]);
      } finally {
        setLoading(false);
      }
    };
    fetchAudit();
  }, []);

  const toggleExpand = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const getActionColor = (action: string) => {
    if (action.includes('auth')) return 'bg-purple-100 text-purple-800';
    if (action.includes('plan')) return 'bg-blue-100 text-blue-800';
    if (action.includes('document')) return 'bg-emerald-100 text-emerald-800';
    if (action.includes('learning')) return 'bg-amber-100 text-amber-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <PageHeader 
        eyebrow="DECISIONS WITH A HISTORY" 
        title="Activity trail"
      />

      {loading ? (
        <div className="flex justify-center p-12"><Spinner size="lg" /></div>
      ) : events.length === 0 ? (
        <EmptyState
          icon={<History className="w-10 h-10 text-muted" />}
          title="No audit events"
          description="The system activity trail is empty."
        />
      ) : (
        <div className="border rounded-md bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/10">
              <tr className="border-b">
                <th className="text-left font-medium p-4 text-muted-foreground w-48">Timestamp</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Action</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Actor ID</th>
                <th className="text-left font-medium p-4 text-muted-foreground">Target ID</th>
                <th className="text-right font-medium p-4 text-muted-foreground">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {events.map((e, idx) => (
                <React.Fragment key={e._id || idx}>
                  <tr className="hover:bg-muted/5 transition-colors">
                    <td className="p-4 text-xs text-muted-foreground whitespace-nowrap">
                      {formatDateTime(e.timestamp || e.created_at || new Date().toISOString())}
                    </td>
                    <td className="p-4">
                      <Badge className={cn("font-mono text-[10px] uppercase", getActionColor(e.action))} variant="default">
                        {e.action}
                      </Badge>
                    </td>
                    <td className="p-4 font-mono text-xs">
                      {e.actor_id ? truncateId(e.actor_id) : '-'}
                    </td>
                    <td className="p-4 font-mono text-xs">
                      {e.target_id ? truncateId(e.target_id) : '-'}
                    </td>
                    <td className="p-4 text-right">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => toggleExpand(e._id || idx.toString())}
                        className="h-8 w-8 p-0"
                      >
                        {expanded[e._id || idx.toString()] ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </Button>
                    </td>
                  </tr>
                  {expanded[e._id || idx.toString()] && (
                    <tr className="bg-muted/10">
                      <td colSpan={5} className="p-4">
                        <pre className="text-xs bg-black/5 p-3 rounded-md overflow-x-auto">
                          {JSON.stringify(e.details || {}, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AuditPage;

