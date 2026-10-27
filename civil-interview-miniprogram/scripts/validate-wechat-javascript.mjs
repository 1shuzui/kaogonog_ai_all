import { readFileSync } from 'node:fs'
import { relative } from 'node:path'
import { parse } from 'acorn'

// Match the build target for all scripts, including native files emitted as assets.
export function validateWeChatJavaScript(files, outputDir) {
  const failures = []
  for (const file of files.filter(file => file.endsWith('.js'))) {
    try {
      parse(readFileSync(file, 'utf8'), { ecmaVersion: 2018, sourceType: 'script' })
    } catch (error) {
      failures.push(`invalid WeChat JavaScript: ${relative(outputDir, file)}: ${error.message}`)
    }
  }
  return failures
}
