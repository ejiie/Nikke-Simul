using System.Collections;
using System.Reflection;

namespace Nikke.Data;

/// <summary>
/// One generic null contract for a deserialized read model: a member or collection/dictionary element that is not
/// annotated nullable must not be null, at any depth. System.Text.Json's RespectNullableAnnotations covers
/// properties and constructor parameters but not collection elements, and typed code that dereferences an element
/// would otherwise throw NullReferenceException (500) or pass the null through (200).
/// Nullable-annotated members may be null here; whether that null is legitimate is a domain rule the caller checks.
/// </summary>
internal static class StrictGraph
{
    public static void RequireNoNullViolations(object root,string errorCode)
    {
        var context=new NullabilityInfoContext();
        var visited=new HashSet<object>(ReferenceEqualityComparer.Instance);
        try{Walk(root,null,"$",context,visited);}
        catch(InvalidDataException ex){throw new InvalidOperationException(errorCode,ex);}
    }
    private static void Walk(object value,NullabilityInfo? info,string path,NullabilityInfoContext context,HashSet<object> visited)
    {
        var type=value.GetType();
        if(type.IsPrimitive || type.IsEnum || value is string or decimal or DateTime or DateTimeOffset or Guid)return;
        if(!visited.Add(value))return;
        if(value is IDictionary dictionary)
        {
            var valueInfo=info is {GenericTypeArguments.Length: 2}?info.GenericTypeArguments[1]:null;
            foreach(DictionaryEntry entry in dictionary)Element(entry.Value,valueInfo,$"{path}[{entry.Key}]",context,visited);
            return;
        }
        if(value is IEnumerable sequence)
        {
            var elementInfo=info?.ElementType??(info is {GenericTypeArguments.Length: 1}?info.GenericTypeArguments[0]:null);
            var index=0;
            foreach(var item in sequence)Element(item,elementInfo,$"{path}[{index++}]",context,visited);
            return;
        }
        foreach(var property in type.GetProperties(BindingFlags.Public|BindingFlags.Instance))
        {
            if(property.GetIndexParameters().Length>0 || !property.CanRead)continue;
            var propertyInfo=context.Create(property);
            var child=property.GetValue(value);
            var childPath=$"{path}.{property.Name}";
            if(child is null)
            {
                if(propertyInfo.ReadState==NullabilityState.NotNull)throw new InvalidDataException($"null at {childPath}");
                continue;
            }
            Walk(child,propertyInfo,childPath,context,visited);
        }
    }
    private static void Element(object? item,NullabilityInfo? elementInfo,string path,NullabilityInfoContext context,HashSet<object> visited)
    {
        if(item is null)
        {
            // Unknown element annotation is treated as non-null: collections in these contracts never carry null items.
            if(elementInfo is null || elementInfo.ReadState!=NullabilityState.Nullable)throw new InvalidDataException($"null at {path}");
            return;
        }
        Walk(item,elementInfo,path,context,visited);
    }
}
