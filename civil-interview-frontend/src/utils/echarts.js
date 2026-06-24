/**
 * PC 图表加载工具只注册当前项目需要的 ECharts 模块，避免普通页面背上完整图表库体积。
 *
 * 能力雷达图已转为稳定优先的隐藏策略，因此这里保留折线趋势等轻量图表能力即可，不扩展会增加维护面的组件。
 *
 * @param 无；模块在导入时注册图表类型和渲染器。
 * @return 导出 ECharts init 与 graphic，供趋势图等组件按需初始化。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
// ECharts 按需引入 - 只加载项目用到的模块
import { use, init, graphic } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer
])

export default { init, graphic }
