import React from 'react';

export default function EventCardSkeleton() {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm flex flex-col h-full animate-pulse">
      {/* Image Skeleton */}
      <div className="h-40 bg-slate-200 dark:bg-slate-800 w-full relative">
        <div className="absolute top-2 right-2 w-16 h-6 bg-slate-300 dark:bg-slate-700 rounded-lg"></div>
      </div>
      
      {/* Content Skeleton */}
      <div className="p-4 flex flex-col flex-1 gap-3">
        {/* Date & Type */}
        <div className="flex justify-between items-center">
             <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded"></div>
             <div className="h-4 w-20 bg-slate-200 dark:bg-slate-800 rounded"></div>
        </div>
        
        {/* Title */}
        <div className="space-y-2">
            <div className="h-5 w-full bg-slate-200 dark:bg-slate-800 rounded"></div>
            <div className="h-5 w-3/4 bg-slate-200 dark:bg-slate-800 rounded"></div>
        </div>
        
        {/* Location & Damage */}
        <div className="grid grid-cols-2 gap-2 mt-2">
            <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
            <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded-lg"></div>
        </div>
        
        {/* Footer */}
        <div className="mt-auto pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
            <div className="h-8 w-24 bg-slate-200 dark:bg-slate-800 rounded-lg"></div>
            <div className="h-6 w-16 bg-slate-200 dark:bg-slate-800 rounded"></div>
        </div>
      </div>
    </div>
  );
}
