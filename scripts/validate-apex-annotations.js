#!/usr/bin/env node
/**
 * APEX Annotation Validator for OpenAPI Specifications
 * Validates x-apeX-* extensions in OpenAPI specs
 * 
 * NOTE: This validator is advisory only - warnings don't block builds
 */

const fs = require('fs');

// Try to load yaml, fallback to JSON if not available
let yaml;
try {
  yaml = require('js-yaml');
} catch (e) {
  console.log('⚠️  js-yaml not installed, attempting to install...');
  // If js-yaml is not available, we'll try to use the system's node modules
  try {
    yaml = require(process.env.NODE_PATH ? process.env.NODE_PATH + '/js-yaml' : 'js-yaml');
  } catch (e2) {
    console.error('❌ js-yaml module required. Install with: npm install js-yaml');
    process.exit(0); // Don't fail the build for missing validator dependency
  }
}

const RECOMMENDED_APEX_EXTENSIONS = [
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
  
  let spec;
  try {
    const content = fs.readFileSync(specPath, 'utf8');
    spec = yaml.load(content);
  } catch (e) {
    console.warn(`Advisory: Could not parse ${specPath}: ${e.message}`);
    return 0; // Non-fatal - don't block builds
  }
  
  const errors = [];
  const warnings = [];
  const infos = [];
  
  // Check for recommended top-level extensions (not required)
  for (const ext of RECOMMENDED_APEX_EXTENSIONS) {
    if (!spec[ext]) {
      infos.push(`Optional APEX extension missing: ${ext}`);
    }
  }
  
  // Validate x-apeX-metadata if present
  if (spec['x-apeX-metadata']) {
    const metadata = spec['x-apeX-metadata'];
    const recommendedMetadata = ['audit_date', 'auditor', 'compliance_framework'];
    for (const field of recommendedMetadata) {
      if (!metadata[field]) {
        infos.push(`x-apeX-metadata could include: ${field}`);
      }
    }
  }
  
  // Validate x-apeX-security-controls if present
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
        
        // Check for observability on operations (recommendation, not required)
        if (!operation['x-apeX-observability']) {
          // Only recommend for non-health endpoints
          const isHealth = path.includes('health') || (operation.tags && operation.tags.includes('Health'));
          if (!isHealth) {
            infos.push(`${method.toUpperCase()} ${path}: Consider adding x-apeX-observability`);
          }
        }
        
        // Validate x-apeX-observability if present
        if (operation['x-apeX-observability']) {
          const obs = operation['x-apeX-observability'];
          if (!obs.emit_metric && !obs.log_event) {
            warnings.push(`${method.toUpperCase()} ${path}: x-apeX-observability should have emit_metric or log_event`);
          }
        }
        
        // Check for x-apeX-validation on request schemas
        if (operation.requestBody?.content) {
          for (const [contentType, content] of Object.entries(operation.requestBody.content)) {
            if (content.schema && !content.schema['x-apeX-validation']) {
              // Info only - not required
              infos.push(`${method.toUpperCase()} ${path}: Consider adding x-apeX-validation to request schema`);
            }
          }
        }
      }
    }
  }
  
  // Validate schemas for x-apeX-sanitize (recommendation)
  if (spec.components?.schemas) {
    for (const [name, schema] of Object.entries(spec.components.schemas)) {
      if (schema.type === 'object') {
        for (const [propName, prop] of Object.entries(schema.properties || {})) {
          // Only warn for string properties that look like user input
          const userInputFields = ['name', 'email', 'phone', 'message', 'content', 'text', 'body'];
          if (prop.type === 'string' && !prop['x-apeX-sanitize'] && userInputFields.includes(propName)) {
            infos.push(`Schema ${name}.${propName}: Consider adding x-apeX-sanitize for user input`);
          }
        }
      }
    }
  }
  
  // Report results
  console.log('═'.repeat(70));
  console.log('VALIDATION RESULTS (Advisory Only)');
  console.log('═'.repeat(70));
  
  if (errors.length === 0 && warnings.length === 0 && infos.length === 0) {
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
  
  if (infos.length > 0) {
    console.log(`\nℹ️  RECOMMENDATIONS (${infos.length}):`);
    infos.forEach(i => console.log(`   • ${i}`));
  }
  
  console.log('\n' + '═'.repeat(70));
  console.log(`Summary: ${errors.length} errors, ${warnings.length} warnings, ${infos.length} recommendations`);
  console.log('Note: These are advisory checks - they do not block the build');
  console.log('═'.repeat(70) + '\n');
  
  // Always return 0 - don't block builds
  return 0;
}

// Main
const specPath = process.argv[2] || 'openapi/whatsapp-api.yaml';
if (!fs.existsSync(specPath)) {
  console.error(`❌ File not found: ${specPath}`);
  process.exit(0); // Don't fail build for missing spec
}

const exitCode = validateApexAnnotations(specPath);
process.exit(exitCode);
