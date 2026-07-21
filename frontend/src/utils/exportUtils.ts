import type ReactECharts from 'echarts-for-react'

export function exportCSV(rows: Record<string, unknown>[], cols: string[], name: string) {
  const bom = '\uFEFF'
  const header = cols.join(',')
  const lines  = rows.map((r) => cols.map((c) => {
    const v = String(r[c] ?? '')
    return v.includes(',') || v.includes('"') || v.includes('\n')
      ? `"${v.replace(/"/g, '""')}"` : v
  }).join(','))
  const blob = new Blob([bom + header + '\n' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = name; a.click()
  URL.revokeObjectURL(url)
}

export async function exportExcel(rows: Record<string, unknown>[], cols: string[], name: string) {
  const XLSX = await import('xlsx-js-style')
  
  const data = rows.map((r) => {
    const obj: Record<string, unknown> = {}
    cols.forEach((c) => { obj[c] = r[c] ?? '' })
    return obj
  })
  
  const ws = XLSX.utils.json_to_sheet(data, { header: cols, cellDates: true })
  
  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:A1')
  const colWidths = cols.map(col => ({ wch: Math.max(col.length + 2, 12) }))
  
  for (let C = range.s.c; C <= range.e.c; ++C) {
    const address = XLSX.utils.encode_cell({ r: 0, c: C })
    if (!ws[address]) continue
    ws[address].s = {
      font: { bold: true, color: { rgb: "FF000000" } },
      fill: { fgColor: { rgb: "FFF3F4F6" } },
      border: { bottom: { style: "thin", color: { rgb: "FFCCCCCC" } } }
    }
  }

  for (let R = 1; R <= range.e.r; ++R) {
    for (let C = range.s.c; C <= range.e.c; ++C) {
      const address = XLSX.utils.encode_cell({ r: R, c: C })
      if (!ws[address]) continue
      
      const val = ws[address].v
      const strVal = String(val)
      
      if (strVal.length > colWidths[C].wch) {
        colWidths[C].wch = Math.min(strVal.length + 2, 50)
      }

      if (typeof val === 'number') {
        if (Number.isInteger(val)) {
          ws[address].z = '0'
        } else {
          ws[address].z = '#,##0.00'
        }
      }
    }
  }
  
  ws['!cols'] = colWidths
  
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Donnees')
  XLSX.writeFile(wb, name)
}

export async function exportPowerBI(rows: Record<string, unknown>[], cols: string[], name: string) {
  const XLSX = await import('xlsx-js-style')

  // Coerce numeric strings to real numbers so Power BI detects types correctly
  const data = rows.map((r) => {
    const obj: Record<string, unknown> = {}
    cols.forEach((c) => {
      const v = r[c]
      if (typeof v === 'string' && v !== '' && !isNaN(Number(v))) {
        obj[c] = Number(v)
      } else {
        obj[c] = v ?? ''
      }
    })
    return obj
  })

  const ws = XLSX.utils.json_to_sheet(data, { header: cols, cellDates: true })

  // Style header row for readability in Power Query
  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:A1')
  const colWidths = cols.map(col => ({ wch: Math.max(col.length + 2, 14) }))
  for (let C = range.s.c; C <= range.e.c; ++C) {
    const addr = XLSX.utils.encode_cell({ r: 0, c: C })
    if (!ws[addr]) continue
    ws[addr].s = {
      font: { bold: true },
      fill: { fgColor: { rgb: 'FF1A56DB' } },
      alignment: { horizontal: 'center' },
    }
    if (colWidths[C].wch < 16) colWidths[C].wch = 16
  }
  ws['!cols'] = colWidths

  const wb = XLSX.utils.book_new()
  // Sheet name MUST be ASCII for Power Query to auto-detect as a Table
  XLSX.utils.book_append_sheet(wb, ws, 'Data')
  XLSX.writeFile(wb, name)
}

export function exportPNG(chartRef: React.RefObject<ReactECharts>, name: string) {
  const ec = chartRef.current?.getEchartsInstance()
  if (!ec) return
  const url = ec.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const a   = document.createElement('a')
  a.href = url; a.download = name; a.click()
}

export function extractDataFromSpec(spec: any): { rows: Record<string, unknown>[], cols: string[] } {
  const rows: Record<string, unknown>[] = []
  let cols: string[] = []

  if (!spec || !spec.series || !spec.series.length) {
    return { rows, cols }
  }

  const type = spec.series[0].type

  if (type === 'pie') {
    const yCol = spec.series[0].name || 'Valeur'
    const xCol = 'Catégorie'
    cols = [xCol, yCol]
    
    const data = spec.series[0].data || []
    data.forEach((item: any) => {
      rows.push({
        [xCol]: item.name,
        [yCol]: item.value
      })
    })
  } else if (type === 'scatter') {
    const xCol = spec.xAxis?.name || 'X'
    const yCol = spec.yAxis?.name || 'Y'
    cols = [xCol, yCol]
    
    const data = spec.series[0].data || []
    data.forEach((item: any) => {
      rows.push({
        [xCol]: item[0],
        [yCol]: item[1]
      })
    })
  } else {
    // bar, line, area
    const xCol = spec.xAxis?.name || 'X'
    cols.push(xCol)
    
    const xData = spec.xAxis?.data || []
    const yCols: string[] = []
    
    spec.series.forEach((s: any, i: number) => {
      const yName = s.name || `Y${i + 1}`
      yCols.push(yName)
      cols.push(yName)
    })
    
    xData.forEach((xVal: any, i: number) => {
      const row: Record<string, unknown> = { [xCol]: xVal }
      spec.series.forEach((s: any, j: number) => {
        row[yCols[j]] = s.data[i]
      })
      rows.push(row)
    })
  }

  return { rows, cols }
}
