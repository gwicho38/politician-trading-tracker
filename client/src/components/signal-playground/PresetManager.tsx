/**
 * PresetManager Component
 * Dropdown for selecting and managing saved weight presets
 */

import { useState } from 'react';
import { Check, ChevronsUpDown, Trash2, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { SignalPreset } from '@/types/signal-playground';

interface PresetManagerProps {
  presets: SignalPreset[];
  userPresets: SignalPreset[];
  systemPresets: SignalPreset[];
  selectedPresetId?: string;
  onSelect: (preset: SignalPreset) => void;
  onDelete?: (presetId: string) => void;
  isLoading?: boolean;
}

export function PresetManager({
  presets,
  userPresets,
  systemPresets,
  selectedPresetId,
  onSelect,
  onDelete,
  isLoading,
}: PresetManagerProps) {
  const [open, setOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SignalPreset | null>(null);

  const selectedPreset = presets.find((p) => p.id === selectedPresetId);

  const handleSelect = (preset: SignalPreset) => {
    onSelect(preset);
    setOpen(false);
  };

  const handleDeleteClick = (e: React.MouseEvent, preset: SignalPreset) => {
    e.stopPropagation();
    setDeleteTarget(preset);
  };

  const confirmDelete = () => {
    if (deleteTarget && onDelete) {
      onDelete(deleteTarget.id);
      setDeleteTarget(null);
    }
  };

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-[200px] justify-between"
            disabled={isLoading}
          >
            {selectedPreset ? (
              <span className="truncate">{selectedPreset.name}</span>
            ) : (
              <span className="text-muted-foreground">Select preset...</span>
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[280px] p-0">
          <Command>
            <CommandInput placeholder="Search presets..." />
            <CommandList>
              <CommandEmpty>No presets found.</CommandEmpty>

              {/* System presets */}
              {systemPresets.length > 0 && (
                <CommandGroup heading="System Presets">
                  {systemPresets.map((preset) => (
                    <CommandItem
                      key={preset.id}
                      value={preset.name}
                      onSelect={() => handleSelect(preset)}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <Check
                          className={cn(
                            'h-4 w-4',
                            selectedPresetId === preset.id
                              ? 'opacity-100'
                              : 'opacity-0'
                          )}
                        />
                        <Star className="h-3 w-3 text-yellow-500" />
                        <span>{preset.name}</span>
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}

              {/* User presets */}
              {userPresets.length > 0 && (
                <>
                  <CommandSeparator />
                  <CommandGroup heading="Your Presets">
                    {userPresets.map((preset) => (
                      <CommandItem
                        key={preset.id}
                        value={preset.name}
                        onSelect={() => handleSelect(preset)}
                        className="flex items-center justify-between group"
                      >
                        <div className="flex items-center gap-2">
                          <Check
                            className={cn(
                              'h-4 w-4',
                              selectedPresetId === preset.id
                                ? 'opacity-100'
                                : 'opacity-0'
                            )}
                          />
                          <span>{preset.name}</span>
                          {preset.is_public && (
                            <Badge variant="outline" className="text-xs">
                              Public
                            </Badge>
                          )}
                        </div>
                        {onDelete && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive"
                            onClick={(e) => handleDeleteClick(e, preset)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        )}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Delete confirmation dialog */}
      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Preset</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteTarget?.name}"? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default PresetManager;
