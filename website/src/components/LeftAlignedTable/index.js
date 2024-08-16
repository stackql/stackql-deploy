import React from 'react';

const LeftAlignedTable = ({ type, required, fields }) => {
    return (
        <div style={{ textAlign: 'left' }}>
            <table style={{ marginLeft: 0 }}>
                <tbody>
                    <tr>
                        <td>Type</td>
                        <td><code>{type}</code></td>
                    </tr>
                    <tr>
                        <td>Required</td>
                        <td><b>{required ? 'Yes' : 'No'}</b></td>
                    </tr>
                    {fields && fields.length > 0 && (
                        <tr>
                            <td>Fields</td>
                            <td>
                                {fields.map((field, index) => (
                                    <span key={index}>
                                        <a href={`#${field.anchor}`}>
                                            <code>{field.name}</code>
                                        </a>
                                        {index < fields.length - 1 && ', '}
                                    </span>
                                ))}
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
            <br />
        </div>
    );
};

export default LeftAlignedTable;
