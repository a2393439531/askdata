<!-- ECharts 封装：按 chartType 渲染 bar / line / pie / table -->
<!-- 约定：bar/line 第一列为 X 轴、其余数值列为 series；pie 取前两列（类别，数值） -->
<template>
  <div class="chart-view">
    <!-- 表格模式：直接渲染 el-table -->
    <el-table
      v-if="chartType === 'table'"
      :data="tableRows"
      border
      stripe
      style="width: 100%"
      max-height="420"
    >
      <el-table-column type="index" label="#" width="55" />
      <el-table-column
        v-for="col in columns"
        :key="col"
        :prop="col"
        :label="col"
        show-overflow-tooltip
        min-width="120"
      />
    </el-table>
    <!-- 无数据时提示 -->
    <el-empty v-else-if="!hasData" description="暂无数据" />
    <!-- 图表模式 -->
    <div v-else ref="chartRef" class="chart-box"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  chartType: { type: String, default: 'bar' }, // bar | line | pie | table
  columns: { type: Array, default: () => [] }, // 列名数组
  rows: { type: Array, default: () => [] } // 二维数据，每行是一个数组
})

const chartRef = ref(null)
let chartInstance = null

// 是否有可渲染的数据（至少 1 列、1 行）
const hasData = computed(() => props.columns.length > 0 && props.rows.length > 0)

// 表格模式用的行对象数组
const tableRows = computed(() =>
  props.rows.map((row) => {
    const obj = {}
    props.columns.forEach((col, i) => {
      obj[col] = row[i]
    })
    return obj
  })
)

// 判断某一列是否为数值列（忽略空值后全部可转数字）
const isNumericColumn = (colIndex) => {
  let hit = false
  for (const row of props.rows) {
    const v = row[colIndex]
    if (v === null || v === undefined || v === '') continue
    hit = true
    if (Number.isNaN(Number(v))) return false
  }
  return hit
}

// 构建 ECharts option
const buildOption = () => {
  const { columns, rows } = props
  if (props.chartType === 'pie') {
    // 饼图：第一列为类别，第二列为数值
    const data = rows.map((row) => ({
      name: String(row[0] ?? '未知'),
      value: Number(row[1]) || 0
    }))
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { type: 'scroll', bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['35%', '65%'],
          data,
          label: { formatter: '{b}: {c}' },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.4)' }
          }
        }
      ]
    }
  }
  // 柱状图 / 折线图：第一列为 X 轴，其余数值列为 series
  const categories = rows.map((row) => String(row[0] ?? ''))
  const series = []
  for (let i = 1; i < columns.length; i++) {
    if (!isNumericColumn(i)) continue
    series.push({
      name: columns[i],
      type: props.chartType === 'line' ? 'line' : 'bar',
      data: rows.map((row) => {
        const n = Number(row[i])
        return Number.isNaN(n) ? null : n
      })
    })
  }
  // 没有数值列时退化为计数展示，避免空图
  if (series.length === 0) {
    series.push({
      name: '计数',
      type: props.chartType === 'line' ? 'line' : 'bar',
      data: rows.map(() => 1)
    })
  }
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: categories, axisLabel: { interval: 0, rotate: 20 } },
    yAxis: { type: 'value' },
    series
  }
}

// 渲染 / 重绘图表
const renderChart = () => {
  if (!chartRef.value || props.chartType === 'table' || !hasData.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  chartInstance.setOption(buildOption(), true)
}

const handleResize = () => {
  if (chartInstance) chartInstance.resize()
}

onMounted(() => {
  nextTick(renderChart)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

// 数据或图表类型变化时重绘
watch(
  () => [props.chartType, props.columns, props.rows],
  () => nextTick(renderChart),
  { deep: true }
)
</script>

<style scoped>
.chart-box {
  width: 100%;
  height: 380px;
}
</style>
