import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Enter your password').max(128, 'Password is too long'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { user, login, isLoading, error, clearError, fetchMe, isInitialized } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  useEffect(() => {
    if (!isInitialized) void fetchMe();
  }, [fetchMe, isInitialized]);

  useEffect(() => {
    if (user) {
      navigate(from, { replace: true });
    }
  }, [user, navigate, from]);

  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const onSubmit = async (data: LoginFormValues) => {
    try {
      await login(data.email, data.password);
      toast.success('Successfully logged in');
      navigate(from, { replace: true });
    } catch (err: any) {
      toast.error('Failed to log in');
    }
  };

  if (user) return null;

  return (
    <div className="min-h-screen flex w-full">
      {/* Left panel - Brand story */}
      <div className="hidden lg:flex flex-col w-1/2 bg-hero-bg text-ink p-12 justify-between">
        <div>
          <div className="flex items-center gap-2 mb-16">
            <div className="w-8 h-8 rounded-md bg-green text-white flex items-center justify-center font-bold text-xl">
              s
            </div>
            <span className="font-semibold text-xl tracking-tight">SkillSprint AI</span>
          </div>
          
          <div className="max-w-md">
            <p className="text-sm font-medium tracking-wider text-muted uppercase mb-4">
              ENTERPRISE ONBOARDING
            </p>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight mb-12">
              Great onboarding. Grounded in <span className="italic font-serif">what matters.</span>
            </h1>
            
            <div className="space-y-8">
              <div className="flex gap-4">
                <div className="text-green font-mono font-bold">01</div>
                <div>
                  <h3 className="font-semibold mb-1">Trusted sources</h3>
                  <p className="text-muted text-sm leading-relaxed">
                    Build training plans directly from your verified corporate policies and compliance documents.
                  </p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="text-green font-mono font-bold">02</div>
                <div>
                  <h3 className="font-semibold mb-1">Relevant learning</h3>
                  <p className="text-muted text-sm leading-relaxed">
                    AI extracts exactly what each role needs to know, saving time and reducing cognitive load.
                  </p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="text-green font-mono font-bold">03</div>
                <div>
                  <h3 className="font-semibold mb-1">Independent checks</h3>
                  <p className="text-muted text-sm leading-relaxed">
                    Human-in-the-loop review ensures all extracted requirements are accurate and approved.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="text-sm text-muted">
          &copy; {new Date().getFullYear()} SkillSprint AI. All rights reserved.
        </div>
      </div>

      {/* Right panel - Login card */}
      <div className="flex flex-col w-full lg:w-1/2 bg-surface items-center justify-center p-8">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl font-bold tracking-tight text-ink">Welcome back</h2>
            <p className="text-muted mt-2 text-sm">
              Sign in to manage your team's learning journey.
            </p>
          </div>

          {error && (
            <div className="p-4 bg-amber/10 border border-amber/20 rounded-lg flex items-start gap-3 text-amber">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-ink" htmlFor="email">
                Email address
              </label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                placeholder="name@company.com"
                {...register('email')}
                className={cn(errors.email && "border-amber focus-visible:ring-amber")}
                disabled={isLoading}
              />
              {errors.email && (
                <p className="text-sm text-amber">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-ink" htmlFor="password">
                  Password
                </label>
              </div>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
                className={cn(errors.password && "border-amber focus-visible:ring-amber")}
                disabled={isLoading}
              />
              {errors.password && (
                <p className="text-sm text-amber">{errors.password.message}</p>
              )}
            </div>

            <Button 
              type="submit" 
              className="w-full bg-green hover:bg-green/90 text-white" 
              disabled={isLoading}
            >
              {isLoading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <div className="text-center lg:text-left text-sm text-muted">
            Need help signing in or resetting your password? Contact your IT administrator.
          </div>
        </div>
      </div>
    </div>
  );
}
