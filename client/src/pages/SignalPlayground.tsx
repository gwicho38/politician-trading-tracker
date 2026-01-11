/**
 * SignalPlayground Page
 * Interactive playground for experimenting with signal generation weights
 */

import { useState, useEffect } from 'react';
import { Save, Calendar, User, LogOut, Sparkles } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { supabase } from '@/integrations/supabase/client';
import type { User as SupabaseUser } from '@supabase/supabase-js';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import { useToast } from '@/hooks/use-toast';
import { useSignalPlayground } from '@/hooks/useSignalPlayground';
import { useSignalPresets } from '@/hooks/useSignalPresets';
import {
  WeightControls,
  SignalPreview,
  PresetManager,
  MLInsights,
} from '@/components/signal-playground';
import { SidebarLayout } from '@/components/layouts/SidebarLayout';

const LOOKBACK_OPTIONS = [
  { value: '30', label: 'Last 30 days' },
  { value: '60', label: 'Last 60 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '180', label: 'Last 6 months' },
  { value: '365', label: 'Last year' },
];

export default function SignalPlayground() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const presetIdFromUrl = searchParams.get('preset');
  const fromShowcase = !!presetIdFromUrl;

  // User auth state
  const [user, setUser] = useState<SupabaseUser | null>(null);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/');
  };

  const getDisplayName = () => {
    if (!user) return '';
    const walletAddress = user.user_metadata?.wallet_address;
    if (walletAddress) {
      return `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`;
    }
    return user.email?.split('@')[0] || 'User';
  };

  // Playground state hook
  const {
    weights,
    updateWeight,
    resetToDefaults,
    loadPreset,
    hasChanges,
    modifiedCount,
    lookbackDays,
    setLookbackDays,
    mlEnhancedCount,
    signals,
    stats,
    isLoading,
    isUpdating,
    error,
  } = useSignalPlayground();

  // Presets hook
  const {
    presets,
    userPresets,
    systemPresets,
    createPresetAsync,
    deletePreset,
    isLoading: presetsLoading,
    isCreating,
  } = useSignalPresets();

  // Save dialog state
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [presetDescription, setPresetDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);

  // Selected preset for tracking
  const [selectedPresetId, setSelectedPresetId] = useState<string>();

  // Load preset from URL if provided (from Showcase)
  useEffect(() => {
    if (presetIdFromUrl && presets.length > 0 && !selectedPresetId) {
      const preset = presets.find((p) => p.id === presetIdFromUrl);
      if (preset) {
        loadPreset(preset);
        setSelectedPresetId(preset.id);
        toast({
          title: 'Strategy loaded',
          description: `"${preset.name}" from showcase has been applied.`,
        });
      }
    }
  }, [presetIdFromUrl, presets, selectedPresetId, loadPreset, toast]);

  // Handle reset to defaults with feedback
  const handleReset = () => {
    resetToDefaults();
    toast({
      title: 'Weights reset',
      description: 'All weights have been reset to default values.',
    });
  };

  // Handle preset selection
  const handlePresetSelect = (preset: typeof presets[0]) => {
    loadPreset(preset);
    setSelectedPresetId(preset.id);
    toast({
      title: 'Preset loaded',
      description: `"${preset.name}" has been applied.`,
    });
  };

  // Handle save preset
  const handleSavePreset = async () => {
    if (!presetName.trim()) {
      toast({
        title: 'Name required',
        description: 'Please enter a name for your preset.',
        variant: 'destructive',
      });
      return;
    }

    if (!user) {
      toast({
        title: 'Not signed in',
        description: 'Please sign in to save presets.',
        variant: 'destructive',
      });
      return;
    }

    console.log('Saving preset:', { name: presetName, weights, user: user.id });

    try {
      const result = await createPresetAsync({
        name: presetName.trim(),
        description: presetDescription.trim() || undefined,
        is_public: isPublic,
        weights,
      });

      console.log('Preset saved:', result);

      toast({
        title: 'Preset saved',
        description: `"${presetName}" has been saved successfully.`,
      });

      // Reset form and close dialog
      setPresetName('');
      setPresetDescription('');
      setIsPublic(false);
      setSaveDialogOpen(false);
    } catch (err) {
      console.error('Failed to save preset:', err);
      toast({
        title: 'Failed to save',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  // Handle delete preset
  const handleDeletePreset = (presetId: string) => {
    deletePreset(presetId);
    if (selectedPresetId === presetId) {
      setSelectedPresetId(undefined);
    }
  };

  return (
    <SidebarLayout>
      <div className="flex flex-col h-full">
        {/* Page Toolbar */}
        <div className="border-b border-border/50 bg-background/80 backdrop-blur-xl">
          <div className="container flex h-12 items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <div>
                <h1 className="text-lg font-semibold">Signal Playground</h1>
              </div>
              {fromShowcase && (
                <span className="text-xs text-muted-foreground flex items-center gap-1 ml-2">
                  <Sparkles className="h-3 w-3" />
                  Trying strategy from showcase
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {/* Lookback period selector */}
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <Select
                  value={String(lookbackDays)}
                  onValueChange={(value) => setLookbackDays(Number(value))}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LOOKBACK_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Preset selector */}
              <PresetManager
                presets={presets}
                userPresets={userPresets}
                systemPresets={systemPresets}
                selectedPresetId={selectedPresetId}
                onSelect={handlePresetSelect}
                onDelete={handleDeletePreset}
                isLoading={presetsLoading}
              />

              {/* User profile */}
              {user ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-2">
                      <User className="h-4 w-4" />
                      <span className="hidden sm:inline">{getDisplayName()}</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem className="text-muted-foreground text-xs">
                      {user.email}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleSignOut} className="text-destructive">
                      <LogOut className="mr-2 h-4 w-4" />
                      Sign out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/auth')}
                >
                  Sign In
                </Button>
              )}
            </div>
          </div>
        </div>

      {/* Main content - resizable panels */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* Left panel - Weight controls */}
          <ResizablePanel defaultSize={35} minSize={25} maxSize={50}>
            <WeightControls
              weights={weights}
              onWeightChange={updateWeight}
              onReset={handleReset}
              onSave={() => setSaveDialogOpen(true)}
              hasChanges={hasChanges}
              modifiedCount={modifiedCount}
              isUpdating={isUpdating}
              canSave={!!user}
            />
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right panel - Signal preview + ML Insights */}
          <ResizablePanel defaultSize={65}>
            <div className="flex flex-col h-full overflow-hidden">
              <div className="flex-1 overflow-y-auto">
                <SignalPreview
                  signals={signals}
                  stats={stats}
                  isLoading={isLoading}
                  isUpdating={isUpdating}
                  error={error as Error | null}
                />
              </div>
              {/* ML Insights panel */}
              <div className="shrink-0 border-t p-4 bg-secondary/20">
                <MLInsights
                  mlEnhancedCount={mlEnhancedCount}
                  totalSignals={signals.length}
                />
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* Save preset dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Weight Preset</DialogTitle>
            <DialogDescription>
              Save your current weight configuration as a reusable preset.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="preset-name">Name</Label>
              <Input
                id="preset-name"
                placeholder="My Custom Preset"
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="preset-description">Description (optional)</Label>
              <Textarea
                id="preset-description"
                placeholder="Describe what this preset is optimized for..."
                value={presetDescription}
                onChange={(e) => setPresetDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="preset-public">Make public</Label>
                <p className="text-xs text-muted-foreground">
                  Allow other users to use this preset
                </p>
              </div>
              <Switch
                id="preset-public"
                checked={isPublic}
                onCheckedChange={setIsPublic}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePreset} disabled={isCreating}>
              <Save className="h-4 w-4 mr-2" />
              {isCreating ? 'Saving...' : 'Save Preset'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </div>
    </SidebarLayout>
  );
}
