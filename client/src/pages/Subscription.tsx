import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { CheckCircle, Crown, Zap, Shield, CreditCard, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { supabase } from '@/integrations/supabase/client';

interface SubscriptionTier {
  id: string;
  name: string;
  description: string;
  price: number;
  interval: 'month' | 'year';
  features: string[];
  popular?: boolean;
  stripePriceId?: string;
}

const SUBSCRIPTION_TIERS: SubscriptionTier[] = [
  {
    id: 'free',
    name: 'Free',
    description: 'Basic access to public politician trading data',
    price: 0,
    interval: 'month',
    features: [
      'View recent politician trades',
      'Basic search and filtering',
      'Limited historical data (30 days)',
      'Community support'
    ]
  },
  {
    id: 'pro',
    name: 'Pro',
    description: 'Advanced trading signals and automation',
    price: 29,
    interval: 'month',
    popular: true,
    features: [
      'Full historical data access',
      'AI-powered trading signals',
      'Manual trading operations',
      'Portfolio tracking and analytics',
      'Email notifications',
      'Priority support',
      'API access'
    ],
    stripePriceId: 'price_pro_monthly' // Replace with actual Stripe price ID
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'Complete trading platform with automation',
    price: 99,
    interval: 'month',
    features: [
      'Everything in Pro',
      'Automated trading execution',
      'Advanced analytics and reporting',
      'Custom signal strategies',
      'Dedicated account manager',
      'White-label options',
      'SLA guarantee'
    ],
    stripePriceId: 'price_enterprise_monthly' // Replace with actual Stripe price ID
  }
];

const SubscriptionPage = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState<string | null>(null);
  const [currentTier, setCurrentTier] = useState<string>('free');

  // Check authentication and current subscription
  useEffect(() => {
    const checkAuthAndSubscription = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate('/auth');
        return;
      }

      // In a real implementation, you'd check the user's subscription status
      // from your backend or Stripe customer data
      setCurrentTier('free'); // Default to free tier
    };

    checkAuthAndSubscription();
  }, [navigate]);

  const handleSubscribe = async (tier: SubscriptionTier) => {
    if (tier.id === 'free') {
      toast({
        title: 'Free Tier',
        description: 'You are already on the free tier. Upgrade to access premium features.',
      });
      return;
    }

    if (!tier.stripePriceId) {
      toast({
        title: 'Coming Soon',
        description: `${tier.name} tier will be available soon.`,
        variant: 'destructive',
      });
      return;
    }

    setLoading(tier.id);

    try {
      // In a real implementation, this would:
      // 1. Create a Stripe checkout session via your backend API
      // 2. Redirect to Stripe Checkout
      // 3. Handle the success/cancel callbacks

      toast({
        title: 'Redirecting to Checkout',
        description: `Redirecting to Stripe to subscribe to ${tier.name}...`,
      });

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));

      // For demo purposes - in real implementation, redirect to Stripe
      toast({
        title: 'Demo Mode',
        description: `Subscription to ${tier.name} would be processed here.`,
      });

    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to start subscription process. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(null);
    }
  };

  const handleManageSubscription = async () => {
    setLoading('manage');

    try {
      // In a real implementation, this would redirect to Stripe Customer Portal
      toast({
        title: 'Customer Portal',
        description: 'Redirecting to subscription management...',
      });

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));

      toast({
        title: 'Demo Mode',
        description: 'Customer portal would open here.',
      });

    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to access subscription management.',
        variant: 'destructive',
      });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Choose Your Plan
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Unlock advanced politician trading insights and automated trading capabilities
          </p>
        </div>

        {/* Current Plan Status */}
        <div className="mb-8">
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-6 w-6 text-primary" />
                  <div>
                    <h3 className="font-semibold text-lg">
                      Current Plan: {SUBSCRIPTION_TIERS.find(t => t.id === currentTier)?.name}
                    </h3>
                    <p className="text-muted-foreground">
                      {SUBSCRIPTION_TIERS.find(t => t.id === currentTier)?.description}
                    </p>
                  </div>
                </div>
                {currentTier !== 'free' && (
                  <Button
                    variant="outline"
                    onClick={handleManageSubscription}
                    disabled={loading === 'manage'}
                  >
                    {loading === 'manage' ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      <>
                        <CreditCard className="mr-2 h-4 w-4" />
                        Manage Subscription
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {SUBSCRIPTION_TIERS.map((tier) => (
            <Card
              key={tier.id}
              className={`relative ${
                tier.popular
                  ? 'border-primary shadow-lg scale-105'
                  : 'border-border'
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground px-3 py-1">
                    Most Popular
                  </Badge>
                </div>
              )}

              <CardHeader className="text-center pb-4">
                <div className="flex items-center justify-center gap-2 mb-2">
                  {tier.id === 'free' && <Shield className="h-5 w-5 text-muted-foreground" />}
                  {tier.id === 'pro' && <Zap className="h-5 w-5 text-primary" />}
                  {tier.id === 'enterprise' && <Crown className="h-5 w-5 text-yellow-500" />}
                  <CardTitle className="text-2xl">{tier.name}</CardTitle>
                </div>

                <CardDescription className="text-base">
                  {tier.description}
                </CardDescription>

                <div className="mt-4">
                  {tier.price === 0 ? (
                    <div className="text-3xl font-bold text-foreground">Free</div>
                  ) : (
                    <div className="text-center">
                      <div className="text-3xl font-bold text-foreground">
                        ${tier.price}
                        <span className="text-lg font-normal text-muted-foreground">
                          /{tier.interval}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </CardHeader>

              <CardContent>
                <Separator className="mb-6" />

                <ul className="space-y-3 mb-6">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full"
                  variant={tier.id === currentTier ? "outline" : "default"}
                  disabled={tier.id === currentTier || loading === tier.id}
                  onClick={() => handleSubscribe(tier)}
                >
                  {loading === tier.id ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : tier.id === currentTier ? (
                    'Current Plan'
                  ) : tier.price === 0 ? (
                    'Get Started'
                  ) : (
                    `Subscribe to ${tier.name}`
                  )}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* FAQ or Additional Info */}
        <div className="text-center">
          <p className="text-muted-foreground mb-4">
            All plans include a 14-day free trial. Cancel anytime.
          </p>
          <p className="text-sm text-muted-foreground">
            Need help choosing a plan? <a href="mailto:support@example.com" className="underline">Contact support</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionPage;