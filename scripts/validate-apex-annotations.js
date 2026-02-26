#!/usr/bin/env node
/**
 * APEX Annotation Validator for OpenAPI Specifications
 * Validates x-apeX-* extensions in OpenAPI specs
 */

const fs = require('fs');
const yaml = require('js-yaml');

const REQUIRED_APEX_EXTENSIONS = [
  'x-apeX-metadata',
  'x-apeX-security-controls'
];

const VALID_SECURITY_CONTROLS = [
  'input_validation',
  'authentication',
  'authorization',
  'rate_limiting',
  'observability',
  'data_protection'
];

function validateApexAnnotations(specPath) {
  console.log(`🔍 Validating APEX annotations in: ${specPath}\n`);
  
  const content = fs.readFileSync(specPath, 'utf8');
  const spec = yaml.load(content);
  
  const errors = [];
  const warnings = [];
  
  // Check for required top-level extensions
  for (const ext of REQUIRED_APEX_EXTENSIONS) {
    if (!spec[ext]) {
      errors.push(`Missing required APEX extension: ${ext}`);
    }
  }
  
  // Validate x-apeX-metadata
  if (spec['x-apeX-metadata']) {
    const metadata = spec['x-apeX-metadata'];
    const requiredMetadata = ['audit_date', 'auditor', 'compliance_framework'];
    for (const field of requiredMetadata) {
      if (!metadata[field]) {
        errors.push(`x-apeX-metadata missing field: ${field}`);
      }
    }
  }
  
  // Validate x-apeX-security-controls
  if (spec['x-apeX-security-controls']) {
    const controls = spec['x-apeX-security-controls'];
    for (const control of Object.keys(controls)) {
      if (!VALID_SECURITY_CONTROLS.includes(control)) {
        warnings.push(`Unknown security control: ${control}`);
      }
    }
  }
  
  // Validate paths for x-apeX extensions
  if (spec.paths) {
    for (const [path, methods] of Object.entries(spec.paths)) {
      for (const [method, operation] of Object.entries(methods)) {
        if (typeof operation !== 'object' || !operation.operationId) continue;
        
        // Check for observability on operations
        if (!operation['x-apeX-observability']) {
          warnings.push(`${method.toUpperCase()} ${path}: Missing x-apeX-observability`);
        }
        
        // Validate x-apeX-observability if present
        if (operation['x-apeX-observability']) {
          const obs = operation['x-apeX-observability'];
          if (!obs.emit_metric) {
            warnings.push(`${method.toUpperCase()} ${path}: x-apeX-observability should emit_metric`);
          }
        }
      }
    }
  }
  
  // Validate schemas for x-apeX-sanitize
  if (spec.components?.schemas) {
    for (const [name, schema] of Object.entries(spec.components.schemas)) {
      if (schema.type === 'object') {
        for (const [propName, prop] of Object.entries(schema.properties || {})) {
          if (prop.type === 'string' && !prop['x-apeX-sanitize'] && propName !== 'id') {
            warnings.push(`Schema ${name}.${propName}: String property without x-apeX-sanitize`);
          }
        }
      }
    }
  }
  
  // Report results
  console.log('═'.repeat(70));
  console.log('VALIDATION RESULTS');
  console.log('═'.repeat(70));
  
  if (errors.length === 0 && warnings.length === 0) {
    console.log('✅ All APEX annotations valid!\n');
    return 0;
  }
  
  if (errors.length > 0) {
    console.log(`\n❌ ERRORS (${errors.length}):`);
    errors.forEach(e => console.log(`   • ${e}`));
  }
  
  if (warnings.length > 0) {
    console.log(`\n⚠️  WARNINGS (${warnings.length}):`);
    warnings.forEach(w => console.log(`   • ${w}`));
  }
  
  console.log('\n' + '═'.repeat(70));
  console.log(`Summary: ${errors.length} errors, ${warnings.length} warnings`);
  console.log('═'.repeat(70) + '\n');
  
  return errors.length > 0 ? 1 : 0;
}

// Main
const specPath = process.argv[2] || 'openapi/whatsapp-api.yaml';
if (!fs.existsSync(specPath)) {
  console.error(`❌ File not found: ${specPath}`);
  process.exit(1);
}

const exitCode = validateApexAnnotations(specPath);
process.exit(exitCode);
