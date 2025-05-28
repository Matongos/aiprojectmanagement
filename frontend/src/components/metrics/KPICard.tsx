"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: number;
  description?: string;
  className?: string;
}

export function KPICard({ title, value, trend, description, className }: KPICardProps) {
  const getTrendIcon = () => {
    if (!trend) return <Minus className="h-4 w-4 text-gray-500" />;
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
        {(trend || description) && (
          <p className="text-xs text-muted-foreground">
            {trend && (
              <span className={getTrendColor()}>
                {trend > 0 ? "+" : ""}
                {trend}%
              </span>
            )}
            {trend && description && " · "}
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
} 