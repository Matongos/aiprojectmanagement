"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ReactNode } from "react";

interface KPICardProps {
  title: string;
  value: ReactNode;
  description?: ReactNode;
  trend?: number;
  isLoading?: boolean;
  className?: string;
}

export function KPICard({
  title,
  value,
  trend,
  description,
  isLoading = false,
  className,
}: KPICardProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-[60px] mb-2" />
          <Skeleton className="h-4 w-[100px] mt-2" />
        </CardContent>
      </Card>
    );
  }

  const getTrendIcon = () => {
    if (typeof trend === 'undefined') return null;
    if (trend === 0) return <Minus className="h-4 w-4 text-gray-500" />;
    return trend > 0 ? (
      <TrendingUp className="h-4 w-4 text-green-500" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-500" />
    );
  };

  const getTrendColor = () => {
    if (!trend) return "text-gray-500";
    return trend > 0 ? "text-green-500" : "text-red-500";
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {getTrendIcon()}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <div className="text-xs text-muted-foreground mt-2">
            {description}
          </div>
        )}
      </CardContent>
    </Card>
  );
} 