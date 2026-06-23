/**
 * Reusable labelled input field with inline error message.
 * Forwards all standard input props.
 */
import { forwardRef, InputHTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label:    string
  error?:   string
  hint?:    string
}

const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, hint, className, id, ...rest }, ref) => {
    const fieldId = id ?? label.toLowerCase().replace(/\s+/g, '-')
    return (
      <div>
        <label
          htmlFor={fieldId}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
        </label>
        <input
          ref={ref}
          id={fieldId}
          className={clsx(
            'w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'transition',
            error
              ? 'border-red-400 bg-red-50 focus:ring-red-400'
              : 'border-gray-300 bg-white hover:border-gray-400',
            className,
          )}
          aria-describedby={error ? `${fieldId}-error` : undefined}
          aria-invalid={!!error}
          {...rest}
        />
        {error && (
          <p id={`${fieldId}-error`} className="mt-1 text-xs text-red-600 flex items-center gap-1">
            <span>⚠</span> {error}
          </p>
        )}
        {hint && !error && (
          <p className="mt-1 text-xs text-gray-400">{hint}</p>
        )}
      </div>
    )
  },
)

FormField.displayName = 'FormField'
export default FormField
