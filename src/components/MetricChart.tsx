import { useEffect, useRef } from 'react'
import { BarChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { init, use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import type { GroupStat } from '../types'

use([BarChart, GridComponent, MarkLineComponent, TooltipComponent, SVGRenderer])

export function MetricChart({ groups, metric }: { groups: GroupStat[]; metric: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = init(ref.current, undefined, { renderer: 'svg' })
    chart.setOption({
      animationDuration: 500,
      grid: { top: 24, right: 24, bottom: 38, left: 54 },
      tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => Number(value).toFixed(4) },
      xAxis: {
        type: 'category', data: groups.map((group) => group.group),
        axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#a8b5c7', fontSize: 12 }, axisTick: { show: false },
      },
      yAxis: {
        type: 'value', name: metric, nameTextStyle: { color: '#7f8da3' }, scale: true,
        splitLine: { lineStyle: { color: '#1e2b3d' } }, axisLabel: { color: '#8492a6' },
      },
      series: [{
        type: 'bar', barMaxWidth: 54,
        data: groups.map((group, index) => ({
          value: group.mean,
          itemStyle: { color: index === 0 ? '#6f8198' : index === 1 ? '#59e3c2' : '#f8c866', borderRadius: [6, 6, 0, 0] },
        })),
        markLine: groups[0]?.mean == null ? undefined : {
          symbol: 'none', silent: true,
          lineStyle: { color: '#8da0ba', type: 'dashed' },
          label: { color: '#a8b5c7', formatter: 'baseline' },
          data: [{ yAxis: groups[0].mean }],
        },
      }],
    })
    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => { window.removeEventListener('resize', resize); chart.dispose() }
  }, [groups, metric])
  return <div ref={ref} className="metric-chart" role="img" aria-label={`${metric} 各实验组均值对比图`} />
}
