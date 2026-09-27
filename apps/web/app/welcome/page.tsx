"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, Lock, ScanText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiRequest, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { BRAND } from "@/lib/brand";

const schema = z.object({
  full_name: z.string().trim().min(1, "Enter your name"),
  organization_name: z.string().trim().min(1, "Enter your company name"),
  email: z.union([z.literal(""), z.string().trim().email("Enter a valid email, or leave it blank")]),
  license_key: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/** First launch of the desktop app. One short form instead of an account:
 *  no password, no email verification. It starts the free trial, or
 *  activates a key straight away for customers who've already bought. */
export default function WelcomePage() {
  const { isDesktop, desktopSetupRequired, billingEnabled, isLoading, me, setupDesktop } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (me) router.replace("/dashboard");
    else if (!isDesktop || !desktopSetupRequired) router.replace("/login");
  }, [isLoading, me, isDesktop, desktopSetupRequired, router]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: "" } });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await setupDesktop({
        full_name: values.full_name,
        organization_name: values.organization_name,
        email: values.email || undefined,
      });
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Setup failed. Please try again.");
      return;
    }
    if (values.license_key?.trim()) {
      try {
        await apiRequest("/api/license/activate", {
          method: "POST",
          body: { key: values.license_key },
        });
      } catch (err) {
        // Setup succeeded; the trial is running. Say what happened to the
        // key and let them fix it in Settings rather than blocking entry.
        const reason = err instanceof ApiError ? err.message : "It could not be activated.";
        router.replace(`/settings?keyError=${encodeURIComponent(reason)}`);
        return;
      }
    }
    router.replace("/dashboard");
  };

  if (isLoading || !isDesktop || !desktopSetupRequired) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="grid w-full max-w-4xl grid-cols-1 overflow-hidden rounded-2xl border border-[var(--border)] bg-surface shadow-sm md:grid-cols-5">
        <aside className="flex flex-col justify-between bg-[linear-gradient(160deg,#4338ca,#312e81)] p-8 text-white md:col-span-2">
          <div>
            <p className="text-sm font-medium uppercase tracking-wider text-indigo-200">Welcome to</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight">{BRAND.name}</p>
            <p className="mt-2 text-indigo-100">{BRAND.tagline}</p>
          </div>
          <ul className="mt-8 space-y-4 text-sm text-indigo-50">
            <li className="flex gap-3">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-teal-300" />
              {billingEnabled
                ? `Every feature free for ${BRAND.trialDays} days. No card, no sign-up.`
                : "Free during early access. Every feature, no card, no sign-up."}
            </li>
            <li className="flex gap-3">
              <Lock className="h-5 w-5 shrink-0 text-teal-300" />
              Your documents never leave this computer. No cloud, no AI service.
            </li>
            <li className="flex gap-3">
              <ScanText className="h-5 w-5 shrink-0 text-teal-300" />
              Reads scanned contracts, Word files, and PDFs.
            </li>
          </ul>
        </aside>

        <main className="p-8 md:col-span-3">
          <Logo className="mb-6" />
          <h1 className="text-xl font-semibold text-foreground">Let&apos;s set up your workspace</h1>
          <p className="mb-6 mt-1 text-sm text-muted-foreground">
            Takes ten seconds. You won&apos;t need a password: {BRAND.name} opens straight into your
            work from now on.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="full_name">Your name</Label>
                <Input id="full_name" autoComplete="name" autoFocus {...register("full_name")} />
                {errors.full_name && (
                  <p className="mt-1 text-sm text-red-600" role="alert">
                    {errors.full_name.message}
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="organization_name">Company</Label>
                <Input id="organization_name" autoComplete="organization" {...register("organization_name")} />
                {errors.organization_name && (
                  <p className="mt-1 text-sm text-red-600" role="alert">
                    {errors.organization_name.message}
                  </p>
                )}
              </div>
            </div>
            <div>
              <Label htmlFor="email">
                Work email <span className="font-normal text-muted-foreground">(optional)</span>
              </Label>
              <Input id="email" type="email" autoComplete="email" {...register("email")} />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600" role="alert">
                  {errors.email.message}
                </p>
              )}
            </div>

            {showKey ? (
              <div>
                <Label htmlFor="license_key">License key</Label>
                <textarea
                  id="license_key"
                  rows={3}
                  placeholder="TMV1.…"
                  className="w-full rounded-md border border-[var(--border)] bg-white px-3 py-2 font-mono text-xs"
                  {...register("license_key")}
                />
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowKey(true)}
                className="text-sm font-medium text-primary hover:underline"
              >
                Already bought {BRAND.name}? Enter your license key
              </button>
            )}

            {serverError && (
              <p className="rounded-md status-critical border px-3 py-2 text-sm" role="alert">
                {serverError}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting
                ? "Setting up…"
                : showKey
                  ? "Activate and get started"
                  : billingEnabled
                    ? `Start my ${BRAND.trialDays}-day free trial`
                    : "Get started, it's free"}
            </Button>
          </form>
        </main>
      </div>
    </div>
  );
}
